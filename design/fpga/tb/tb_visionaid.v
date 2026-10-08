// Testbench for the VisionAid FPGA safety island (simulation only - NOT hardware measurements).
//
// Behavioural models: 3 x RCWL-1601 ultrasonic sensors (echo width = 2 d / 343 m/s, 300 us
// response delay), a TF-Luna LiDAR streaming 9-byte frames at 100 Hz, and the Raspberry Pi
// (heartbeat toggle every 100 ms, UART commands, status-frame decoder).
//
// Checks:
//   T1 distance accuracy              T4 drop-off detection (LiDAR)
//   T2 echo-edge -> motor-on latency  T5 Pi heartbeat lost -> alerts continue + AI-offline chirp
//   T3 status frames to the Pi        T6 disconnected sensor -> fault flag + FAULT_N
`timescale 1ns/1ps
module tb_visionaid;
    // 27 MHz clock
    reg clk = 1'b0;
    always #18.518 clk = ~clk;
    localparam real CLK_NS = 37.037;

    reg rst_n = 1'b0;
    wire [2:0] trig;
    reg  [2:0] echo = 3'b000;
    reg  lidar_line = 1'b1;
    reg  pi_tx_line = 1'b1;
    wire pi_rx_line;
    reg  hb = 1'b0;
    wire fault_n, mot_l, mot_r, buzz;
    wire [5:0] led_n;
    reg  btn_read_n = 1'b1, btn_mode_n = 1'b1, btn_quiet_n = 1'b1;

    visionaid_top dut (
        .clk(clk), .rst_n(rst_n), .us_trig(trig), .us_echo(echo), .lidar_tx(), .lidar_rx(lidar_line),
        .pi_txd(pi_tx_line), .pi_rxd(pi_rx_line), .pi_hb(hb), .fpga_fault_n(fault_n),
        .mot_l(mot_l), .mot_r(mot_r), .buzz(buzz),
        .btn_read_n(btn_read_n), .btn_mode_n(btn_mode_n), .btn_quiet_n(btn_quiet_n), .led_n(led_n));

    integer errors = 0;
    task check(input cond, input [8*72-1:0] msg);
        begin
            if (cond) $display("[%7.1f ms] PASS  %0s", $realtime / 1e6, msg);
            else begin $display("[%7.1f ms] FAIL  %0s", $realtime / 1e6, msg); errors = errors + 1; end
        end
    endtask

    // ---------------------------------------------------------------- ultrasonic sensor models
    integer dist_mm [0:2];        // object distance per sensor, mm (> 5000 = nothing)
    reg     connected [0:2];
    realtime echo_fall_t [0:2];   // time of the most recent echo falling edge
    genvar g;
    generate for (g = 0; g < 3; g = g + 1) begin : sensor
        always @(negedge trig[g]) if (connected[g]) begin : ping
            real w_us;
            #(300_000);                                       // sensor response delay 300 us
            w_us = (dist_mm[g] > 5000) ? 38000.0 : 2.0 * dist_mm[g] / 0.343;   // 343 m/s = 0.343 mm/us
            echo[g] = 1'b1;
            #(w_us * 1000.0);
            echo[g] = 1'b0;
            echo_fall_t[g] = $realtime;
        end
    end endgenerate

    // ---------------------------------------------------------------- UART helpers (115200 baud)
    localparam real BIT_NS = 1_000_000_000.0 / 115200.0;
    // (Verilog tasks cannot drive a signal passed as an argument, so one task per line.)
    task lidar_send(input [7:0] b);
        integer i;
        begin
            lidar_line = 1'b0; #(BIT_NS);
            for (i = 0; i < 8; i = i + 1) begin lidar_line = b[i]; #(BIT_NS); end
            lidar_line = 1'b1; #(BIT_NS);
        end
    endtask
    task pi_send(input [7:0] b);
        integer i;
        begin
            pi_tx_line = 1'b0; #(BIT_NS);
            for (i = 0; i < 8; i = i + 1) begin pi_tx_line = b[i]; #(BIT_NS); end
            pi_tx_line = 1'b1; #(BIT_NS);
        end
    endtask

    // TF-Luna model: frame every 10 ms
    integer lidar_cm = 150;
    reg     lidar_on = 1'b1;
    task send_lidar_frame;
        reg [7:0] f [0:8];
        reg [7:0] s;
        integer i;
        begin
            f[0] = 8'h59; f[1] = 8'h59; f[2] = lidar_cm[7:0]; f[3] = lidar_cm[15:8];
            f[4] = 8'hE8; f[5] = 8'h03;                    // amplitude 1000
            f[6] = 8'h00; f[7] = 8'h09;                    // temperature (ignored)
            s = 0; for (i = 0; i < 8; i = i + 1) s = s + f[i];
            f[8] = s;
            for (i = 0; i < 9; i = i + 1) lidar_send(f[i]);
        end
    endtask
    initial begin
        #(2_000_000);
        forever begin
            if (lidar_on) send_lidar_frame;
            #(10_000_000 - 9 * 10 * BIT_NS);
        end
    end

    // Pi heartbeat
    reg hb_on = 1'b1;
    initial forever begin #(100_000_000); if (hb_on) hb = ~hb; end

    task pi_cmd(input [7:0] addr, input [15:0] val);
        begin
            pi_send(8'h5A); pi_send(addr); pi_send(val[15:8]); pi_send(val[7:0]);
            pi_send(addr + val[15:8] + val[7:0]);
        end
    endtask

    // ---------------------------------------------------------------- Pi-side status decoder
    reg [7:0] rxb;
    reg [7:0] fr [0:10];
    integer fi = 0, frames_ok = 0, frames_bad = 0;
    reg [15:0] st_d0, st_d1, st_d2, st_lidar;
    reg [7:0]  st_flags;
    always @(negedge pi_rx_line) begin : pi_uart_rx
        integer i;
        #(BIT_NS * 1.5);
        for (i = 0; i < 8; i = i + 1) begin rxb[i] = pi_rx_line; #(BIT_NS); end
        if (fi == 0 && rxb != 8'hA5) fi = 0;
        else begin
            fr[fi] = rxb; fi = fi + 1;
            if (fi == 11) begin : chk
                reg [7:0] s;
                fi = 0;
                s = 0; for (i = 1; i < 10; i = i + 1) s = s + fr[i];
                if (s == fr[10]) begin
                    frames_ok = frames_ok + 1;
                    st_d0 = {fr[1], fr[2]}; st_d1 = {fr[3], fr[4]}; st_d2 = {fr[5], fr[6]};
                    st_lidar = {fr[7], fr[8]}; st_flags = fr[9];
                end else frames_bad = frames_bad + 1;
            end
        end
    end

    // ---------------------------------------------------------------- latency monitor (T2)
    // Measures time from the echo falling edge (end of the measurement) to the first clock on
    // which the motor output is high, for every 'clear/warn -> urgent' transition on the left channel.
    integer  lat_n = 0;
    real     lat_max = 0.0, lat_sum = 0.0;
    reg      armed = 1'b0;
    realtime arm_t;
    always @(posedge clk) begin
        if (dut.zl == 2'd3 && !armed && dut.hl.zone_d != 2'd3) begin
            armed <= 1'b1;
            arm_t <= echo_fall_t[0];
        end
        if (armed && mot_l) begin : got
            real l;
            l = $realtime - arm_t;
            lat_n = lat_n + 1; lat_sum = lat_sum + l;
            if (l > lat_max) lat_max = l;
            armed <= 1'b0;
        end
    end

    // ---------------------------------------------------------------- scenario
    realtime t0;
    integer  k;
    initial begin
        $dumpfile("sim/visionaid.vcd");
        $dumpvars(1, tb_visionaid);
        $dumpvars(1, dut);
        $dumpoff;
        dist_mm[0] = 1500; dist_mm[1] = 2500; dist_mm[2] = 9999;
        connected[0] = 1; connected[1] = 1; connected[2] = 1;
        #(1_000); rst_n = 1'b1;
        $display("VisionAid safety-island simulation (27 MHz, 3 x 33 ms ultrasonic slots)");

        // ---------- T1: distance accuracy after one full sensor cycle
        #(110_000_000);
        check(dut.d0 >= 1499 && dut.d0 <= 1501, "T1 left  sensor 1500 mm measured within +/-1 mm");
        check(dut.d1 >= 2499 && dut.d1 <= 2501, "T1 right sensor 2500 mm measured within +/-1 mm");
        check(dut.d2 == 16'hFFFF,               "T1 head  sensor: nothing in range reported as 0xFFFF");
        $display("      measured: L=%0d mm  R=%0d mm  H=%0h", dut.d0, dut.d1, dut.d2);
        check(dut.zl == 2'd2 && dut.zr == 2'd1, "T1 zones: 1.5 m -> WARN, 2.5 m -> INFO");

        // ---------- T2: obstacle moves into the urgent zone, several times
        for (k = 0; k < 4; k = k + 1) begin
            dist_mm[0] = 700 + 50 * k;           // urgent (< 1000 mm)
            if (k == 1) $dumpon;
            #(100_000_000);
            if (k == 1) $dumpoff;
            dist_mm[0] = 1600;                   // back to warn
            #(100_000_000);
        end
        $display("      echo-edge -> motor-on latency: %0d events, mean %0.1f ns, max %0.1f ns (%0.1f clock cycles)",
                 lat_n, lat_sum / lat_n, lat_max, lat_max / CLK_NS);
        check(lat_n >= 4 && lat_max < 1_000.0, "T2 worst-case echo -> motor latency < 1 us (target <= 1 ms)");

        // ---------- T3: status frames
        check(frames_ok >= 20 && frames_bad == 0, "T3 Pi status frames received with valid checksums");
        $display("      frames ok=%0d bad=%0d, last: L=%0d R=%0d LiDAR=%0d cm flags=%b",
                 frames_ok, frames_bad, st_d0, st_d1, st_lidar, st_flags);

        // ---------- T4: LiDAR drop-off (Pi sets floor baseline 150 cm, then the floor 'drops' 25 cm)
        pi_cmd(8'd4, 16'd150);
        #(50_000_000);
        check(dut.base_cm == 16'd150, "T4 Pi command accepted: LiDAR baseline = 150 cm");
        check(!dut.drop, "T4 no drop-off alert on a flat floor");
        t0 = $realtime;
        lidar_cm = 175;
        wait (dut.drop == 1'b1);
        $display("      drop-off detected %0.1f ms after the floor reading changed (3-frame filter at 100 Hz)",
                 ($realtime - t0) / 1e6);
        check(($realtime - t0) < 50e6, "T4 drop-off alert within 50 ms");
        #(1_000_000);
        check(mot_l | mot_r | buzz | dut.zone_l == 2'd3, "T4 drop-off drives both motors (urgent) + buzzer");
        lidar_cm = 150;
        #(1_700_000_000);                          // > 1.5 s hold
        check(!dut.drop, "T4 drop-off alert clears after hold time on a flat floor");

        // ---------- T5: Pi heartbeat lost -> AI offline, alerts still work
        hb_on = 1'b0;
        t0 = $realtime;
        wait (dut.ai_offline == 1'b1);
        $display("      AI-offline flagged %0.0f ms after the last possible heartbeat edge", ($realtime - t0) / 1e6);
        check(($realtime - t0) < 1_000e6, "T5 AI offline detected within 1 s");
        dist_mm[0] = 600;
        #(110_000_000);
        check(dut.zl == 2'd3, "T5 obstacle alert still works with the Pi offline (FPGA-only path)");

        // ---------- T6: head sensor unplugged
        connected[2] = 0;
        #(400_000_000);
        check(dut.us_fault[2] && !fault_n, "T6 unplugged sensor -> fault flag + FAULT_N low");

        $display("RESULT: %0s (%0d failures)", errors == 0 ? "ALL TESTS PASSED" : "FAILURES", errors);
        $finish;
    end
endmodule
