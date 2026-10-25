`timescale 1ns/1ps
// 1-cycle RGB/control pipeline. All scalar status latched at VS rising.
// External heat_read_* is combinational from a stable, complete front buffer;
// heat bank may change only at VS; heat values are pre-normalised 0..255.
// No implicit sensor/AI data: validity gates every element. Grid 96x54.
module video_status_overlay #(
    parameter integer FRAME_WIDTH=1920,FRAME_HEIGHT=1080,
    parameter integer PANEL_X=16,PANEL_Y=80,HEAT_SCALE=4,BORDER=4,TEXT_X=320,TEXT_Y=16
)(
    input wire clk,rst_n,in_hs,in_vs,in_de,
    input wire [23:0] in_rgb,
    input wire thermal_valid,environment_valid,ai_valid,alarm_active,prediction_valid,
    input wire [7:0] person_score,event_score,event_type,
    input wire signed [15:0] temperature_centi,
    input wire [15:0] humidity_centi,
    input wire [6:0] prediction_x,prediction_y,
    input wire [31:0] status_frame_id,display_frame_id,
    input wire heat_pixel_valid,
    input wire [7:0] heat_level,
    output wire [9:0] heat_address,
    output wire heat_request,
    output reg out_hs,out_vs,out_de,
    output reg [23:0] out_rgb
);
    reg vs_d,de_d;
    reg [15:0] x,y;
    reg tv,ev,av,al,pv;
    reg [7:0] ps,es,et;
    reg [15:0] px,py;
    reg signed [15:0] tc;
    reg [15:0] rh;
    reg [31:0] fid;
    `include "osd_font5x7.vh"
    reg [127:0] textline;
    reg [7:0] character;
    reg [34:0] bitmap;
    integer abs_tc,col,row,bit_index;
    always @* begin
        abs_tc=tc<0?-tc:tc;
        textline="                ";
        col=0;row=0;bit_index=0;character=32;bitmap=0;
        if(x>=TEXT_X&&x<TEXT_X+96&&y>=TEXT_Y&&y<TEXT_Y+32) begin
            col=(x-TEXT_X)/6;row=(y-TEXT_Y)/8;
            case(row)
            0: begin
                textline="T ----.-- C     ";
                if(ev) begin
                    textline[111:104]=tc<0?"-":"+";
                    textline[103:96]="0"+(abs_tc/10000)%10;
                    textline[95:88]="0"+(abs_tc/1000)%10;
                    textline[87:80]="0"+(abs_tc/100)%10;
                    textline[71:64]="0"+(abs_tc/10)%10;
                    textline[63:56]="0"+abs_tc%10;
                end
            end
            1: begin
                textline="RH ---.--       ";
                if(ev) begin
                    textline[103:96]="0"+(rh/10000)%10;
                    textline[95:88]="0"+(rh/1000)%10;
                    textline[87:80]="0"+(rh/100)%10;
                    textline[71:64]="0"+(rh/10)%10;
                    textline[63:56]="0"+rh%10;
                end
            end
            2: begin
                textline="AI --- FS --- T-";
                if(av) begin
                    textline[103:96]="0"+ps/100;textline[95:88]="0"+(ps/10)%10;textline[87:80]="0"+ps%10;
                    textline[47:40]="0"+es/100;textline[39:32]="0"+(es/10)%10;textline[31:24]="0"+es%10;
                    textline[7:0]=hexchar(et[3:0]);
                end
            end
            3: begin
                textline="FRAME 00000000  ";
                textline[79:16]={hexchar(fid[31:28]),hexchar(fid[27:24]),hexchar(fid[23:20]),hexchar(fid[19:16]),hexchar(fid[15:12]),hexchar(fid[11:8]),hexchar(fid[7:4]),hexchar(fid[3:0])};
            end
            endcase
            character=textline[127-col*8 -:8];bitmap=glyph(character);
            bit_index=34-((y-TEXT_Y)%8)*5-(x-TEXT_X)%6;
        end
    end
    wire inside_heat=x>=PANEL_X && x<PANEL_X+32*HEAT_SCALE && y>=PANEL_Y && y<PANEL_Y+24*HEAT_SCALE;
    assign heat_address=inside_heat ? ((y-PANEL_Y)/HEAT_SCALE)*32+(x-PANEL_X)/HEAT_SCALE : 0;
    assign heat_request=in_de&&inside_heat&&tv;
    reg [23:0] pixel;
    always @* begin
        pixel=in_rgb;
        if(in_de) begin
            // Four 12x12 health squares: IR/env/AI/armed alarm. Grey means absent.
            if(y>=16&&y<28&&x>=16&&x<76) begin
                if(x<28) pixel=tv?24'h00cc80:24'h606060;
                else if(x>=32&&x<44) pixel=ev?24'h00cc80:24'h606060;
                else if(x>=48&&x<60) pixel=av?24'h00cc80:24'h606060;
                else if(x>=64) pixel=al?24'hff3000:24'h606060;
            end
            // Separate score bars: width 0..255; no score when AI invalid/mismatched.
            if(y>=36&&y<44&&x>=16&&x<272) pixel=av&&x-16<ps?24'h00aaff:24'h303030;
            if(y>=48&&y<56&&x>=16&&x<272) pixel=av&&x-16<es?24'hffaa00:24'h303030;
            // Event type as four bits, documented as a diagnostic (not text OSD).
            if(y>=60&&y<68&&x>=16&&x<48) pixel=av&&et[(x-16)/8]?24'hffffff:24'h303030;
            if(inside_heat) begin
                if(!tv||!heat_pixel_valid) pixel=((x/4+y/4)%2)?24'h606060:24'h303030;
                else pixel={heat_level,8'h20,~heat_level};
            end
            if(x>=TEXT_X&&x<TEXT_X+96&&y>=TEXT_Y&&y<TEXT_Y+32)
                pixel=(x-TEXT_X)%6<5&&(y-TEXT_Y)%8<7&&bitmap[bit_index]?24'hffffff:24'h202020;
            if(pv && ((x+3>=px&&x<=px+3&&y==py)||(y+3>=py&&y<=py+3&&x==px))) pixel=24'h00ffff;
            if(al && (x<BORDER||y<BORDER||x>=FRAME_WIDTH-BORDER||y>=FRAME_HEIGHT-BORDER)) pixel=24'hff0000;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            vs_d<=0;de_d<=0;x<=0;y<=0;tv<=0;ev<=0;av<=0;al<=0;pv<=0;
            ps<=0;es<=0;et<=0;px<=0;py<=0;tc<=0;rh<=0;fid<=0;out_hs<=0;out_vs<=0;out_de<=0;out_rgb<=0;
        end else begin
            vs_d<=in_vs;de_d<=in_de;
            out_hs<=in_hs;out_vs<=in_vs;out_de<=in_de;out_rgb<=pixel;
            if(in_vs&&!vs_d) begin
                x<=0;y<=0;tv<=thermal_valid;ev<=environment_valid&&humidity_centi<=10000;
                tc<=temperature_centi;rh<=humidity_centi;fid<=display_frame_id;
                av<=ai_valid&&status_frame_id==display_frame_id;
                // Alarm is current event state; it can remain held across frames.
                al<=alarm_active;
                pv<=prediction_valid&&status_frame_id==display_frame_id&&prediction_x<96&&prediction_y<54;
                ps<=person_score;es<=event_score;et<=event_type;
                px<=prediction_x*FRAME_WIDTH/96;py<=prediction_y*FRAME_HEIGHT/54;
            end else if(in_de) x<=x+1'b1;
            else if(de_d) begin x<=0;y<=y+1'b1;end
        end
    end
endmodule
