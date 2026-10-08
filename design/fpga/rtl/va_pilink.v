`timescale 1ns/1ps
// VisionAid - UART link to the Raspberry Pi 5 (115200 8N1).
//
// FPGA -> Pi, every 20 ms, 11-byte status frame:
//   0xA5, dL_hi, dL_lo, dR_hi, dR_lo, dH_hi, dH_lo, lidar_hi, lidar_lo, flags, checksum
//   checksum = low 8 bits of the sum of bytes 1..9
//   flags: [0] fault L  [1] fault R  [2] fault H  [3] lidar stale  [4] drop-off alert
//          [5] READ pressed (since last frame)  [6] MODE pressed  [7] quiet mode
// Pi -> FPGA, 5-byte command: 0x5A, addr, val_hi, val_lo, checksum (= addr + val_hi + val_lo)
//   addr 1 = urgent threshold mm, 2 = warn threshold mm, 3 = info threshold mm,
//        4 = lidar floor baseline cm, 5 = quiet mode (0/1)
// The Pi can only CHANGE SETTINGS within safe limits; it can never switch the alert path off:
// thresholds are clamped (urgent >= 500 mm) and quiet mode silences only the 'info' zone.
module va_pilink #(parameter CLKS_PER_BIT = 234, parameter PERIOD_MS = 20) (
    input  wire        clk,
    input  wire        rst,
    input  wire        tick_ms,
    input  wire        rx,            // synchronized
    output wire        tx,
    input  wire [15:0] dist0, dist1, dist2, lidar_cm,
    input  wire [7:0]  flags_in,      // bits 0..4 live status; 5,6 are replaced by latched events
    input  wire        ev_read, ev_mode,
    output reg  [15:0] th_urgent, th_warn, th_info, baseline_cm,
    output reg         quiet
);
    // ---------------- receive commands
    wire [7:0] rb;
    wire       rv;
    va_uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) urx (.clk(clk), .rst(rst), .rx(rx), .data(rb), .valid(rv));
    reg [2:0] ci;
    reg [7:0] ca, ch, cl;
    wire [15:0] cv = {ch, cl};
    always @(posedge clk) begin
        if (rst) begin
            ci <= 0;
            th_urgent <= 16'd1000; th_warn <= 16'd2000; th_info <= 16'd3000;   // defaults (mm)
            baseline_cm <= 16'd0; quiet <= 1'b0;
        end else if (rv) begin
            case (ci)
                3'd0: ci <= (rb == 8'h5A) ? 3'd1 : 3'd0;
                3'd1: begin ca <= rb; ci <= 3'd2; end
                3'd2: begin ch <= rb; ci <= 3'd3; end
                3'd3: begin cl <= rb; ci <= 3'd4; end
                default: begin
                    ci <= 0;
                    if (rb == ca + ch + cl) case (ca)
                        8'd1: th_urgent   <= (cv < 16'd500)  ? 16'd500  : cv;
                        8'd2: th_warn     <= (cv < 16'd1000) ? 16'd1000 : cv;
                        8'd3: th_info     <= (cv > 16'd4000) ? 16'd4000 : cv;
                        8'd4: baseline_cm <= cv;
                        8'd5: quiet       <= cl[0];
                        default: ;
                    endcase
                end
            endcase
        end
    end

    // ---------------- transmit status
    reg [7:0]  frame [0:10];
    reg [3:0]  ti;
    reg        sending, start;
    reg [5:0]  t_ms;
    reg        lr, lm;               // latched button events
    wire       busy;
    reg  [7:0] chk;
    va_uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) utx (.clk(clk), .rst(rst), .data(frame[ti]), .start(start),
                                                   .tx(tx), .busy(busy));
    integer k;
    always @(posedge clk) begin
        start <= 1'b0;
        if (rst) begin
            ti <= 0; sending <= 1'b0; t_ms <= 0; lr <= 1'b0; lm <= 1'b0;
        end else begin
            if (ev_read) lr <= 1'b1;
            if (ev_mode) lm <= 1'b1;
            if (tick_ms) t_ms <= (t_ms == PERIOD_MS - 1) ? 6'd0 : t_ms + 1'b1;
            if (!sending && tick_ms && t_ms == PERIOD_MS - 1) begin
                frame[0] <= 8'hA5;
                frame[1] <= dist0[15:8];    frame[2] <= dist0[7:0];
                frame[3] <= dist1[15:8];    frame[4] <= dist1[7:0];
                frame[5] <= dist2[15:8];    frame[6] <= dist2[7:0];
                frame[7] <= lidar_cm[15:8]; frame[8] <= lidar_cm[7:0];
                frame[9] <= {quiet, lm, lr, flags_in[4:0]};
                frame[10] <= dist0[15:8] + dist0[7:0] + dist1[15:8] + dist1[7:0] + dist2[15:8] + dist2[7:0]
                           + lidar_cm[15:8] + lidar_cm[7:0] + {quiet, lm, lr, flags_in[4:0]};
                lr <= ev_read; lm <= ev_mode;
                ti <= 0; sending <= 1'b1; start <= 1'b1;
            end else if (sending && !busy && !start) begin
                if (ti == 4'd10) sending <= 1'b0;
                else begin ti <= ti + 1'b1; start <= 1'b1; end
            end
        end
    end
endmodule
