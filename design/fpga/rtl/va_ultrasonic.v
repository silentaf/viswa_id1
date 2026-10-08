`timescale 1ns/1ps
// VisionAid - ultrasonic sequencer for 3 x RCWL-1601 (HC-SR04-compatible) sensors.
//
// The sensors are fired one after another (never together) so one sensor cannot hear another's
// ping (crosstalk). Each slot: 10 us trigger -> wait for echo rise -> time echo high in us ->
// distance -> wait until the slot ends. With SLOT_US = 33 000 the update period per direction is
// 3 x 33 ms = 99 ms (design target <= 100 ms).
//
// Distance: d[mm] = t_echo[us] * 343 m/s / 2 = t * 0.1715  ->  (t * 11239) >> 16  (error < 0.01 %).
// The distance is registered the clock after the echo falling edge is seen (after the 2-flop
// synchronizer), so the decision path adds only a few 37 ns clock cycles.
module va_ultrasonic #(
    parameter SLOT_US      = 33000,   // time per sensor slot
    parameter TRIG_US      = 10,      // trigger pulse width
    parameter RISE_TO_US   = 5000,    // echo must rise within this time, else 'no response'
    parameter MAX_ECHO_US  = 30000,   // longer echo = nothing in range
    parameter FAULT_COUNT  = 3        // consecutive no-response slots before a sensor fault
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        tick_us,
    input  wire [2:0]  echo,          // synchronized
    output reg  [2:0]  trig,
    output reg  [15:0] dist0, dist1, dist2,   // mm; 16'hFFFF = nothing in range
    output reg  [2:0]  meas_valid,    // one-cycle strobe per channel when a new distance is stored
    output reg  [2:0]  fault          // sensor not responding (disconnected / dead)
);
    localparam S_TRIG = 2'd0, S_RISE = 2'd1, S_HIGH = 2'd2, S_GUARD = 2'd3;
    reg [1:0]  state;
    reg [1:0]  ch;
    reg [15:0] slot_t;     // us since slot start
    reg [15:0] echo_t;     // us echo has been high
    reg [1:0]  miss [0:2];
    reg        echo_d;
    wire       e = echo[ch];
    wire [31:0] mm_full = echo_t * 32'd11239;
    wire [15:0] mm = mm_full[31:16];

    integer i;
    always @(posedge clk) begin
        meas_valid <= 3'b000;
        if (rst) begin
            state <= S_TRIG; ch <= 2'd0; slot_t <= 0; echo_t <= 0; trig <= 3'b000; fault <= 3'b000;
            dist0 <= 16'hFFFF; dist1 <= 16'hFFFF; dist2 <= 16'hFFFF; echo_d <= 1'b0;
            for (i = 0; i < 3; i = i + 1) miss[i] <= 0;
        end else begin
            echo_d <= e;
            if (tick_us) slot_t <= slot_t + 1'b1;
            case (state)
                S_TRIG: begin
                    trig[ch] <= 1'b1;
                    if (tick_us && slot_t == TRIG_US - 1) begin
                        trig  <= 3'b000;
                        state <= S_RISE;
                    end
                end
                S_RISE: begin
                    if (e && !echo_d) begin
                        echo_t <= 0;
                        state  <= S_HIGH;
                    end else if (slot_t >= RISE_TO_US) begin
                        // sensor did not answer at all
                        if (miss[ch] == FAULT_COUNT - 1) fault[ch] <= 1'b1;
                        else miss[ch] <= miss[ch] + 1'b1;
                        state <= S_GUARD;
                    end
                end
                S_HIGH: begin
                    if (tick_us && e) echo_t <= echo_t + 1'b1;
                    if (!e || echo_t >= MAX_ECHO_US) begin
                        // echo ended (or too long = nothing in range): store distance immediately
                        case (ch)
                            2'd0: dist0 <= (echo_t >= MAX_ECHO_US) ? 16'hFFFF : mm;
                            2'd1: dist1 <= (echo_t >= MAX_ECHO_US) ? 16'hFFFF : mm;
                            default: dist2 <= (echo_t >= MAX_ECHO_US) ? 16'hFFFF : mm;
                        endcase
                        meas_valid[ch] <= 1'b1;
                        miss[ch]  <= 0;
                        fault[ch] <= 1'b0;
                        state <= S_GUARD;
                    end
                end
                S_GUARD: begin
                    if (slot_t >= SLOT_US - 1) begin
                        slot_t <= 0;
                        ch     <= (ch == 2'd2) ? 2'd0 : ch + 1'b1;
                        state  <= S_TRIG;
                    end
                end
            endcase
        end
    end
endmodule
