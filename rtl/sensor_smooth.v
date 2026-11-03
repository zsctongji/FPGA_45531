// Scalar sensor preprocessing, separate from sensor calibration and I2C.
// Values are signed 16-bit integers; application chooses scale (e.g. 0.01 C).
// Out-of-range values and jumps from the preceding accepted sample are rejected.
// Window=4. Warm-up average uses the number of accepted samples; divide truncates
// toward zero. No backpressure: at most one sample per clock, no state on bubbles.
module sensor_smooth #(
    parameter integer MIN_VALUE = -4000,
    parameter integer MAX_VALUE = 12500,
    parameter integer MAX_STEP = 2000
) (
    input wire clk,
    input wire rst,
    input wire sample_valid,
    input wire signed [15:0] sample_data,
    output reg out_valid,
    output reg rejected,
    output reg signed [15:0] mean_data
);
    reg signed [15:0] history [0:3];
    reg [1:0] wr_index;
    reg [2:0] count;
    reg signed [31:0] sum;
    reg signed [15:0] last;
    integer i;
    integer value;
    integer delta;
    integer next_sum;
    integer divisor;

    always @* begin
        value = $signed(sample_data);
        delta = value - $signed(last);
        if (delta < 0) delta = -delta;
        next_sum = sum + value;
        if (count == 4) next_sum = next_sum - $signed(history[wr_index]);
        divisor = (count < 4) ? count + 1 : 4;
    end

    always @(posedge clk) begin
        if (rst) begin
            wr_index <= 0;
            count <= 0;
            sum <= 0;
            last <= 0;
            out_valid <= 0;
            rejected <= 0;
            mean_data <= 0;
            for (i = 0; i < 4; i = i + 1) history[i] <= 0;
        end else begin
            out_valid <= 0;
            rejected <= 0;
            if (sample_valid) begin
                if ((value < MIN_VALUE) || (value > MAX_VALUE) ||
                    ((count != 0) && (delta > MAX_STEP))) begin
                    rejected <= 1;
                end else begin
                    history[wr_index] <= sample_data;
                    wr_index <= wr_index + 1'b1;
                    if (count < 4) count <= count + 1'b1;
                    sum <= next_sum;
                    last <= sample_data;
                    mean_data <= next_sum / divisor;
                    out_valid <= 1;
                end
            end
        end
    end
endmodule
