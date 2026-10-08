`timescale 1ns/1ps
// VisionAid FPGA safety island - top level (Sipeed Tang Nano 9K, GW1NR-9, 27 MHz).
//
// Safety rule: the ultrasonic / LiDAR -> haptic / buzzer path is computed entirely in this FPGA.
// The Raspberry Pi only receives status and may tune thresholds within clamped limits. If the Pi
// stops its heartbeat, alerts continue unchanged and a distinct "AI offline" chirp is played.
//
// Alert mapping:
//   forward-left sensor  -> left motor          head-level sensor -> both motors
//   forward-right sensor -> right motor         drop-off (LiDAR)  -> both motors continuous + buzzer
//   sensor / LiDAR fault -> buzzer "check device" (3 short beeps every 5 s) + FPGA_FAULT_N low
module visionaid_top #(
    parameter CLK_HZ  = 27_000_000,
    parameter BAUD    = 115_200,
    parameter SLOT_US = 33000
) (
    input  wire       clk,            // pin 52, 27 MHz
    input  wire       rst_n,          // pin 4, on-board button S1
    output wire [2:0] us_trig,        // L, R, H
    input  wire [2:0] us_echo,
    output wire       lidar_tx,       // to TF-Luna RXD (not used: TF-Luna streams by default)
    input  wire       lidar_rx,       // from TF-Luna TXD
    input  wire       pi_txd,         // Pi GPIO14 -> FPGA
    output wire       pi_rxd,         // FPGA -> Pi GPIO15
    input  wire       pi_hb,          // Pi GPIO17 heartbeat
    output wire       fpga_fault_n,   // -> Pi GPIO27, low = fault
    output wire       mot_l,
    output wire       mot_r,
    output wire       buzz,
    input  wire       btn_read_n,
    input  wire       btn_mode_n,
    input  wire       btn_quiet_n,
    output wire [5:0] led_n           // on-board LEDs (active low): status
);
    localparam CPB = CLK_HZ / BAUD;

    // ---------------- reset, ticks, input synchronizers
    reg [3:0] rst_sh = 4'hF;
    always @(posedge clk) rst_sh <= {rst_sh[2:0], ~rst_n};
    wire rst = rst_sh[3];

    wire tick_us, tick_ms;
    va_tick #(.DIV(CLK_HZ / 1_000_000)) t_us (.clk(clk), .rst(rst), .tick(tick_us));
    reg [9:0] us_cnt;
    reg       tick_ms_r;
    always @(posedge clk) begin
        tick_ms_r <= 1'b0;
        if (rst) us_cnt <= 0;
        else if (tick_us) begin
            if (us_cnt == 10'd999) begin us_cnt <= 0; tick_ms_r <= 1'b1; end
            else us_cnt <= us_cnt + 1'b1;
        end
    end
    assign tick_ms = tick_ms_r;

    wire [2:0] echo_s;
    wire lidar_rx_s, pi_txd_s, hb_s, b_read_s, b_mode_s, b_quiet_s;
    va_sync s0 (.clk(clk), .rst(rst), .d(us_echo[0]), .q(echo_s[0]));
    va_sync s1 (.clk(clk), .rst(rst), .d(us_echo[1]), .q(echo_s[1]));
    va_sync s2 (.clk(clk), .rst(rst), .d(us_echo[2]), .q(echo_s[2]));
    va_sync #(.RESET_VAL(1'b1)) s3 (.clk(clk), .rst(rst), .d(lidar_rx),    .q(lidar_rx_s));
    va_sync #(.RESET_VAL(1'b1)) s4 (.clk(clk), .rst(rst), .d(pi_txd),      .q(pi_txd_s));
    va_sync s5 (.clk(clk), .rst(rst), .d(pi_hb), .q(hb_s));
    va_sync #(.RESET_VAL(1'b1)) s6 (.clk(clk), .rst(rst), .d(btn_read_n),  .q(b_read_s));
    va_sync #(.RESET_VAL(1'b1)) s7 (.clk(clk), .rst(rst), .d(btn_mode_n),  .q(b_mode_s));
    va_sync #(.RESET_VAL(1'b1)) s8 (.clk(clk), .rst(rst), .d(btn_quiet_n), .q(b_quiet_s));

    // ---------------- sensing
    wire [15:0] d0, d1, d2;
    wire [2:0]  mv, us_fault;
    va_ultrasonic #(.SLOT_US(SLOT_US)) us (.clk(clk), .rst(rst), .tick_us(tick_us), .echo(echo_s),
        .trig(us_trig), .dist0(d0), .dist1(d1), .dist2(d2), .meas_valid(mv), .fault(us_fault));

    wire [7:0] lb;
    wire       lv;
    va_uart_rx #(.CLKS_PER_BIT(CPB)) lrx (.clk(clk), .rst(rst), .rx(lidar_rx_s), .data(lb), .valid(lv));
    wire [15:0] lidar_cm, th_u, th_w, th_i, base_cm;
    wire        lidar_stale, drop, quiet_pi;
    va_lidar lid (.clk(clk), .rst(rst), .tick_ms(tick_ms), .rx_data(lb), .rx_valid(lv),
        .baseline_cm(base_cm), .dist_cm(lidar_cm), .stale(lidar_stale), .drop(drop));
    assign lidar_tx = 1'b1;

    // ---------------- buttons, quiet mode
    wire lvl_r, lvl_m, lvl_q, ev_r, ev_m, ev_q;
    va_debounce db_r (.clk(clk), .rst(rst), .tick_ms(tick_ms), .btn_n(b_read_s),  .level(lvl_r), .pressed(ev_r));
    va_debounce db_m (.clk(clk), .rst(rst), .tick_ms(tick_ms), .btn_n(b_mode_s),  .level(lvl_m), .pressed(ev_m));
    va_debounce db_q (.clk(clk), .rst(rst), .tick_ms(tick_ms), .btn_n(b_quiet_s), .level(lvl_q), .pressed(ev_q));
    reg quiet_btn;
    always @(posedge clk) if (rst) quiet_btn <= 1'b0; else if (ev_q) quiet_btn <= ~quiet_btn;
    wire quiet = quiet_btn | quiet_pi;

    // ---------------- zones and patterns
    wire [1:0] zl, zr, zh;
    va_zone zL (.clk(clk), .rst(rst), .update(mv[0]), .dmm(d0), .th_urgent(th_u), .th_warn(th_w), .th_info(th_i), .zone(zl));
    va_zone zR (.clk(clk), .rst(rst), .update(mv[1]), .dmm(d1), .th_urgent(th_u), .th_warn(th_w), .th_info(th_i), .zone(zr));
    va_zone zH (.clk(clk), .rst(rst), .update(mv[2]), .dmm(d2), .th_urgent(th_u), .th_warn(th_w), .th_info(th_i), .zone(zh));

    // quiet mode drops only the 'info' level; warn / urgent / drop-off are never silenced
    wire [1:0] ql = (quiet && zl == 2'd1) ? 2'd0 : zl;
    wire [1:0] qr = (quiet && zr == 2'd1) ? 2'd0 : zr;
    wire [1:0] qh = (quiet && zh == 2'd1) ? 2'd0 : zh;
    wire [1:0] zone_l = drop ? 2'd3 : ((ql > qh) ? ql : qh);
    wire [1:0] zone_r = drop ? 2'd3 : ((qr > qh) ? qr : qh);
    va_haptic hl (.clk(clk), .rst(rst), .tick_ms(tick_ms), .zone(zone_l), .motor(mot_l));
    va_haptic hr (.clk(clk), .rst(rst), .tick_ms(tick_ms), .zone(zone_r), .motor(mot_r));

    // ---------------- watchdog, faults, buzzer
    wire ai_offline;
    va_watchdog #(.TIMEOUT_MS(750)) wd (.clk(clk), .rst(rst), .tick_ms(tick_ms), .hb(hb_s), .ai_offline(ai_offline));
    wire any_fault = |us_fault | lidar_stale;
    assign fpga_fault_n = ~any_fault;

    // buzzer: drop-off = 4 Hz beeping; fault = 3 beeps every 5 s; AI offline = 2 chirps on entry
    reg [12:0] bt;          // ms in a 5 s cycle
    reg        ai_d;
    reg [9:0]  chirp;       // ms remaining of the AI-offline chirp sequence
    always @(posedge clk) begin
        if (rst) begin bt <= 0; ai_d <= 1'b0; chirp <= 0; end
        else begin
            ai_d <= ai_offline;
            if (tick_ms) bt <= (bt == 13'd4999) ? 13'd0 : bt + 1'b1;
            if (ai_offline && !ai_d) chirp <= 10'd600;
            else if (tick_ms && chirp != 0) chirp <= chirp - 1'b1;
        end
    end
    wire beep_drop  = drop && (bt[7:0] < 8'd125);                                   // ~4 Hz
    wire beep_fault = any_fault && ((bt < 13'd150) || (bt >= 13'd300 && bt < 13'd450) ||
                                    (bt >= 13'd600 && bt < 13'd750));              // 3 beeps / 5 s
    wire beep_ai    = (chirp > 10'd450) || (chirp > 10'd150 && chirp < 10'd300);    // 2 chirps
    assign buzz = beep_drop | beep_fault | beep_ai;

    // ---------------- Pi link
    va_pilink #(.CLKS_PER_BIT(CPB)) pl (.clk(clk), .rst(rst), .tick_ms(tick_ms), .rx(pi_txd_s), .tx(pi_rxd),
        .dist0(d0), .dist1(d1), .dist2(d2), .lidar_cm(lidar_cm),
        .flags_in({3'b000, drop, lidar_stale, us_fault}), .ev_read(ev_r), .ev_mode(ev_m),
        .th_urgent(th_u), .th_warn(th_w), .th_info(th_i), .baseline_cm(base_cm), .quiet(quiet_pi));

    // ---------------- on-board LEDs (active low)
    assign led_n = ~{ai_offline, any_fault, drop, quiet, mot_r, mot_l};
endmodule
