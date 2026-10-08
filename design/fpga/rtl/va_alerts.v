`timescale 1ns/1ps
// VisionAid - distance -> zone classification and haptic / buzzer pattern generation.

// Zone with hysteresis: 0 = clear, 1 = info (< th_info), 2 = warn (< th_warn), 3 = urgent (< th_urgent).
// A zone is entered immediately when the distance crosses a threshold (fast warning) and left only
// when the distance is HYST_MM beyond it (prevents flicker at the boundary).
module va_zone #(parameter HYST_MM = 50) (
    input  wire        clk,
    input  wire        rst,
    input  wire        update,
    input  wire [15:0] dmm,
    input  wire [15:0] th_urgent, th_warn, th_info,
    output reg  [1:0]  zone
);
    wire [1:0] raw = (dmm < th_urgent) ? 2'd3 : (dmm < th_warn) ? 2'd2 : (dmm < th_info) ? 2'd1 : 2'd0;
    wire [15:0] th_cur = (zone == 2'd3) ? th_urgent : (zone == 2'd2) ? th_warn : th_info;
    always @(posedge clk) begin
        if (rst) zone <= 2'd0;
        else if (update) begin
            if (raw >= zone) zone <= raw;                                   // closer: react now
            else if (dmm >= th_cur + HYST_MM) zone <= raw;                // farther: with hysteresis
        end
    end
endmodule

// Pattern generator for one motor. Pulse rate encodes distance:
//   zone 3 urgent : continuous
//   zone 2 warn   : 80 ms on / 120 ms off (5 Hz)
//   zone 1 info   : 60 ms on / 440 ms off (2 Hz)
// When the zone gets more urgent, the pattern restarts in its ON phase, so the motor turns on in
// the same clock cycle as the zone change (no waiting for the pattern phase).
// The output is PWM-limited (DUTY/256 at ~26 kHz) so a 3 V coin motor is not overdriven at 3.3 V.
module va_haptic #(parameter DUTY = 8'd232) (
    input  wire       clk,
    input  wire       rst,
    input  wire       tick_ms,
    input  wire [1:0] zone,
    output wire       motor
);
    reg [1:0] zone_d;
    reg [8:0] t;          // ms within pattern period
    reg [7:0] pwm;
    reg       on;
    wire [8:0] on_ms  = (zone == 2'd2) ? 9'd80  : 9'd60;
    wire [8:0] per_ms = (zone == 2'd2) ? 9'd200 : 9'd500;
    always @(posedge clk) begin
        if (rst) begin
            zone_d <= 2'd0; t <= 0; pwm <= 0;
        end else begin
            zone_d <= zone;
            pwm    <= pwm + 1'b1;
            if (zone > zone_d) t <= 0;                       // restart pattern in ON phase
            else if (tick_ms) t <= (t >= per_ms - 1) ? 9'd0 : t + 1'b1;
        end
    end
    always @(*) begin
        case (zone)
            2'd3:    on = 1'b1;
            2'd2,
            2'd1:    on = (t < on_ms);
            default: on = 1'b0;
        endcase
    end
    assign motor = on & (pwm < DUTY);
endmodule

// TF-Luna frame parser (9 bytes: 0x59 0x59 DistL DistH AmpL AmpH TempL TempH Checksum)
// and drop-off detector: distance to the floor ahead suddenly longer than the calibrated baseline
// by more than DROP_CM for DROP_FRAMES consecutive frames -> step down / curb / pit ahead.
module va_lidar #(
    parameter DROP_CM     = 15,
    parameter DROP_FRAMES = 3,
    parameter MIN_AMP     = 100,       // TF-Luna: amplitude < 100 means unreliable distance
    parameter STALE_MS    = 200,       // no valid frame for this long -> lidar fault
    parameter HOLD_MS     = 1500       // keep the drop alert on at least this long
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        tick_ms,
    input  wire [7:0]  rx_data,
    input  wire        rx_valid,
    input  wire [15:0] baseline_cm,    // 0 = not calibrated -> detector disabled
    output reg  [15:0] dist_cm,
    output reg         stale,
    output reg         drop
);
    reg [3:0]  idx;
    reg [7:0]  b [0:7];
    reg [7:0]  sum;
    reg [1:0]  over;
    reg [7:0]  age_ms;
    reg [10:0] hold;
    always @(posedge clk) begin
        if (rst) begin
            idx <= 0; sum <= 0; dist_cm <= 0; stale <= 1'b1; drop <= 1'b0; over <= 0; age_ms <= 0; hold <= 0;
        end else begin
            if (tick_ms) begin
                if (age_ms < STALE_MS) age_ms <= age_ms + 1'b1;
                else stale <= 1'b1;
                if (hold != 0) hold <= hold - 1'b1;
                else if (drop && over == 0) drop <= 1'b0;
            end
            if (rx_valid) begin
                if (idx == 0) begin                         // header byte 1
                    idx <= (rx_data == 8'h59) ? 4'd1 : 4'd0;
                end else if (idx == 1) begin                // header byte 2
                    idx <= (rx_data == 8'h59) ? 4'd2 : 4'd0;
                    sum <= 8'hB2;                           // 0x59 + 0x59
                end else if (idx < 8) begin                 // payload bytes 2..7
                    b[idx[2:0]] <= rx_data;
                    sum <= sum + rx_data;
                    idx <= idx + 1'b1;
                end else begin                              // checksum byte
                    idx <= 0;
                    if (rx_data == sum && {b[5], b[4]} >= MIN_AMP) begin   // checksum + signal ok
                        dist_cm <= {b[3], b[2]};
                        age_ms  <= 0;
                        stale   <= 1'b0;
                        if (baseline_cm != 0 && {b[3], b[2]} > baseline_cm + DROP_CM) begin
                            if (over == DROP_FRAMES - 1) begin
                                drop <= 1'b1;
                                hold <= HOLD_MS;
                            end else over <= over + 1'b1;
                        end else over <= 0;
                    end
                end
            end
        end
    end
endmodule

// Heartbeat watchdog: the Pi toggles PI_HB at least every 250 ms while its software is healthy.
// No edge for TIMEOUT_MS -> ai_offline. The alert path does not depend on the Pi in any way.
module va_watchdog #(parameter TIMEOUT_MS = 1000) (
    input  wire clk,
    input  wire rst,
    input  wire tick_ms,
    input  wire hb,                 // synchronized
    output reg  ai_offline
);
    reg hb_d;
    reg [10:0] t;
    always @(posedge clk) begin
        if (rst) begin hb_d <= 1'b0; t <= 0; ai_offline <= 1'b1; end
        else begin
            hb_d <= hb;
            if (hb != hb_d) begin t <= 0; ai_offline <= 1'b0; end
            else if (tick_ms) begin
                if (t >= TIMEOUT_MS - 1) ai_offline <= 1'b1;
                else t <= t + 1'b1;
            end
        end
    end
endmodule
