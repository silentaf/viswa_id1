`timescale 1ns/1ps
// VisionAid safety island - small shared building blocks.
// Target: Gowin GW1NR-9 (Tang Nano 9K), 27 MHz clock. Verilog-2001.

// Two-flop synchronizer for asynchronous inputs (echo pins, UART RX, buttons, heartbeat).
module va_sync #(parameter RESET_VAL = 1'b0) (
    input  wire clk,
    input  wire rst,
    input  wire d,
    output wire q
);
    reg [1:0] s;
    always @(posedge clk) begin
        if (rst) s <= {2{RESET_VAL}};
        else     s <= {s[0], d};
    end
    assign q = s[1];
endmodule

// Free-running tick generator: one-cycle pulse every DIV clocks.
module va_tick #(parameter DIV = 27) (
    input  wire clk,
    input  wire rst,
    output reg  tick
);
    localparam W = (DIV > 1) ? $clog2(DIV) : 1;
    reg [W-1:0] cnt;
    always @(posedge clk) begin
        if (rst) begin
            cnt  <= 0;
            tick <= 1'b0;
        end else if (cnt == DIV - 1) begin
            cnt  <= 0;
            tick <= 1'b1;
        end else begin
            cnt  <= cnt + 1'b1;
            tick <= 1'b0;
        end
    end
endmodule

// Button debouncer: output follows the (synchronized, active-low) input only after it has been
// stable for STABLE_MS milliseconds. 'pressed' is a one-cycle pulse on a debounced press.
module va_debounce #(parameter STABLE_MS = 10) (
    input  wire clk,
    input  wire rst,
    input  wire tick_ms,
    input  wire btn_n,      // synchronized, active low (10k pull-up on the board)
    output reg  level,      // 1 = held down
    output reg  pressed
);
    reg [$clog2(STABLE_MS + 1)-1:0] cnt;
    always @(posedge clk) begin
        pressed <= 1'b0;
        if (rst) begin
            cnt   <= 0;
            level <= 1'b0;
        end else if (~btn_n == level) begin
            cnt <= 0;
        end else if (tick_ms) begin
            if (cnt == STABLE_MS - 1) begin
                cnt     <= 0;
                level   <= ~btn_n;
                pressed <= ~btn_n;
            end else begin
                cnt <= cnt + 1'b1;
            end
        end
    end
endmodule

// 8N1 UART receiver. CLKS_PER_BIT = f_clk / baud (27 MHz / 115200 = 234).
module va_uart_rx #(parameter CLKS_PER_BIT = 234) (
    input  wire       clk,
    input  wire       rst,
    input  wire       rx,       // synchronized, idle high
    output reg  [7:0] data,
    output reg        valid
);
    localparam IDLE = 2'd0, START = 2'd1, BITS = 2'd2, STOP = 2'd3;
    reg [1:0]  state;
    reg [8:0]  cnt;
    reg [2:0]  bitn;
    reg [7:0]  sh;
    always @(posedge clk) begin
        valid <= 1'b0;
        if (rst) begin
            state <= IDLE;
            cnt   <= 0;
            bitn  <= 0;
        end else case (state)
            IDLE:  if (!rx) begin state <= START; cnt <= 0; end
            START: if (cnt == CLKS_PER_BIT / 2 - 1) begin
                       cnt <= 0;
                       state <= rx ? IDLE : BITS;     // glitch filter: start bit must still be low
                       bitn <= 0;
                   end else cnt <= cnt + 1'b1;
            BITS:  if (cnt == CLKS_PER_BIT - 1) begin
                       cnt <= 0;
                       sh  <= {rx, sh[7:1]};
                       if (bitn == 3'd7) state <= STOP;
                       bitn <= bitn + 1'b1;
                   end else cnt <= cnt + 1'b1;
            STOP:  if (cnt == CLKS_PER_BIT - 1) begin
                       cnt   <= 0;
                       state <= IDLE;
                       if (rx) begin data <= sh; valid <= 1'b1; end   // framing error -> drop byte
                   end else cnt <= cnt + 1'b1;
        endcase
    end
endmodule

// 8N1 UART transmitter.
module va_uart_tx #(parameter CLKS_PER_BIT = 234) (
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] data,
    input  wire       start,
    output reg        tx,
    output wire       busy
);
    reg [8:0] cnt;
    reg [3:0] bitn;
    reg [9:0] sh;
    reg       active;
    assign busy = active;
    always @(posedge clk) begin
        if (rst) begin
            tx <= 1'b1; active <= 1'b0; cnt <= 0; bitn <= 0;
        end else if (!active) begin
            tx <= 1'b1;
            if (start) begin
                sh <= {1'b1, data, 1'b0};
                active <= 1'b1; cnt <= 0; bitn <= 0;
            end
        end else begin
            tx <= sh[0];
            if (cnt == CLKS_PER_BIT - 1) begin
                cnt <= 0;
                sh  <= {1'b1, sh[9:1]};
                if (bitn == 4'd9) active <= 1'b0;
                bitn <= bitn + 1'b1;
            end else cnt <= cnt + 1'b1;
        end
    end
endmodule
