`timescale 1ns/1ps
module tb_a_overlay;
    localparam W=480,H=180;
    reg clk=0;always #5 clk=~clk;
    reg rst=0,hs=0,vs=0,de=0,tv=0,ev=0,av=0,alarm=0,pv=0;
    reg [7:0] ps=192,es=128,et=1;
    reg signed [15:0] tc=-525;
    reg [15:0] rh=5678;
    reg [31:0] sf=7,df=7;
    wire oh,ov,od,heatreq;
    wire [9:0] heataddr;
    wire [23:0] rgb;
    integer checks=0,fd;
    video_status_overlay #(.FRAME_WIDTH(W),.FRAME_HEIGHT(H),.HEAT_SCALE(1)) dut(
        .clk(clk),.rst_n(rst),.in_hs(hs),.in_vs(vs),.in_de(de),.in_rgb(24'h101820),
        .thermal_valid(tv),.environment_valid(ev),.ai_valid(av),.alarm_active(alarm),.prediction_valid(pv),
        .person_score(ps),.event_score(es),.event_type(et),.temperature_centi(tc),.humidity_centi(rh),
        .prediction_x(7'd30),.prediction_y(7'd20),.status_frame_id(sf),.display_frame_id(df),
        .heat_pixel_valid(1'b1),.heat_level(8'd64),.heat_address(heataddr),.heat_request(heatreq),
        .out_hs(oh),.out_vs(ov),.out_de(od),.out_rgb(rgb));
    task tick;begin @(posedge clk);#1;if({oh,ov,od}!={hs,vs,de})$fatal(1,"control pipeline");checks++;end endtask
    task frame(input integer f);
        reg [23:0] expected;
        begin
            @(negedge clk);vs=1;tick();@(negedge clk);vs=0;tick();
            if(f==1)begin fd=$fopen("a_overlay.ppm","wb");$fwrite(fd,"P6\n480 180\n255\n");end
            for(integer y=0;y<H;y++) begin
                for(integer x=0;x<W;x++) begin
                    @(negedge clk);de=1;hs=(x%2)==0;
                    if(x==240&&y==40)begin ps=7;tc=9999;end // no tearing inside frame
                    if(x>=16&&x<48&&y>=80&&y<104&&heataddr!=(y-80)*32+x-16)$fatal(1,"heat address");
                    tick();
                    if(f==1)$fwrite(fd,"%c%c%c",rgb[23:16],rgb[15:8],rgb[7:0]);
                    if(x==22&&y==20&&rgb!==(f==0?24'h606060:24'h00cc80))$fatal(1,"IR status");
                    if(x==200&&y==40&&rgb!==(f==1?24'h00aaff:24'h303030))$fatal(1,"score/ID gating");
                    if(x==20&&y==84&&f>0&&rgb!==24'h4020bf)$fatal(1,"thermal");
                    if(x==150&&y==66&&rgb!==(f==1?24'h00ffff:24'h101820))$fatal(1,"prediction mapping/ID");
                    if(x==0&&y==0&&rgb!==(f==1?24'hff0000:24'h101820))$fatal(1,"alarm border");
                    if(x==321&&y==16&&f==1&&dut.textline!=="T -005.25 C     ")$fatal(1,"temperature text %s",dut.textline);
                    if(x==321&&y==24&&f==1&&dut.textline!=="RH 056.78       ")$fatal(1,"humidity text %s",dut.textline);
                    if(x==321&&y==32&&f==1&&dut.textline!=="AI 192 FS 128 T1")$fatal(1,"score text %s",dut.textline);
                end
                @(negedge clk);de=0;tick();tick();
            end
            if(f==1)$fclose(fd);
        end
    endtask
    initial begin
        repeat(3)@(posedge clk);@(negedge clk);rst=1;frame(0);
        tv=1;ev=1;av=1;alarm=1;pv=1;ps=192;tc=-525;frame(1);
        sf=8;alarm=0;ps=192;tc=-525;frame(2);
        $display("PASS tb_a_overlay cycles=%0d frames=3 ppm=SYNTHETIC",checks);$finish;
    end
    initial begin #4000000;$fatal(1,"timeout");end
endmodule
