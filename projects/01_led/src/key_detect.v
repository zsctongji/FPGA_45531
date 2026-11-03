/*-----------------------------------------------------------------------

CONFIDENTIAL IN CONFIDENCE
This confidential and proprietary software may be only used as authorized
by a licensing agreement from  EdgeWang (Thereturnofbingo).
In the event of publication, the following notice is applicable:
Copyright (C) 2023-20xx  EdgeWang Corporation
The entire notice above must be reproduced on all authorized copies.
Author				:		EdgeWang
Technology blogs 	: 	
Email Address 		: 		
Filename			:		key_detect
Date				:		2023-06-06
Description			:		
Modification History	:
Date			By			Version			Change Description
=========================================================================
23/6/6		EdgeWang	1.0				Original

****************************************************************/


module key_detect #(
    parameter integer CLK_FREQUENCY_MHz = 50,
    parameter integer DEBOUNCE_MS = 15
)(
    input wire i_key,
    input wire clk,
    input wire rst_n,
    output reg key_sw_en
);
    localparam integer MAX_CNT = CLK_FREQUENCY_MHz * 1000 * DEBOUNCE_MS - 1;
    (* syn_preserve = 1 *) reg [1:0] key_sync;
    reg stable_key;
    reg [31:0] stable_count;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            key_sync <= 2'b11;
            stable_key <= 1'b1;
            stable_count <= 0;
            key_sw_en <= 0;
        end else begin
            key_sync <= {key_sync[0], i_key};
            key_sw_en <= 0;
            if (key_sync[1] == stable_key)
                stable_count <= 0;
            else if (stable_count == MAX_CNT) begin
                stable_count <= 0;
                stable_key <= key_sync[1];
                // One pulse after a debounced press followed by a debounced release.
                key_sw_en <= key_sync[1];
            end else
                stable_count <= stable_count + 1'b1;
        end
    end
endmodule
