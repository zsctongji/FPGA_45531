`timescale 1ns/1ps
module tb_video_motion_display;
    localparam W=8,H=6;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,hs=0,vs=0,de=0;
    reg [7:0] gray=0;
    wire oh,ov,od,sv,cv,motion,error,alarm;
    wire [7:0] r,g,b;
    wire [31:0] changed;
    video_motion_display #(.FRAME_WIDTH(W),.FRAME_HEIGHT(H),.STEP_X(2),.STEP_Y(2),.MIN_CHANGED(2),.HOLD_FRAMES(2),.BORDER(1)) dut(
        .clk(clk),.rst_n(rst_n),.in_hs(hs),.in_vs(vs),.in_de(de),.in_gray(gray),
        .out_hs(oh),.out_vs(ov),.out_de(od),.out_r(r),.out_g(g),.out_b(b),
        .stats_valid(sv),.comparison_valid(cv),.motion_detected(motion),.frame_error(error),.changed_count(changed),.motion_alarm(alarm));
    integer ec[0:31];reg ev[0:31];integer head=0,tail=0;
    integer previous[0:11],image[0:11];reg history=0;
    integer refx=0,refy=0,checks=0,red=0,errors=0,frame_index=-1;
    integer frame_red[0:15];reg prev_vs=0,prev_de=0;
    reg expect_red;reg [23:0] expect_rgb;reg exp_h,exp_v,exp_d;
    always @(posedge clk) begin
        if(!rst_n) begin refx=0;refy=0;prev_vs=0;prev_de=0; end
        else begin
            expect_red=de && alarm && (refx==0 || refx>=W-1 || refy==0 || refy>=H-1);
            expect_rgb=expect_red ? 24'hff0000 : {gray,gray,gray};
            exp_h=hs;exp_v=vs;exp_d=de;
            if(vs && !prev_vs) begin refx=0;refy=0;end
            else if(de) refx=refx+1;
            else if(prev_de) begin refx=0;refy=refy+1;end
            prev_vs=vs;prev_de=de;
            #1;
            if({oh,ov,od} !== {exp_h,exp_v,exp_d} || {r,g,b} !== expect_rgb) $fatal(1,"pixel/control/border alignment cycle=%0d",checks);
            if(de && expect_red) begin red=red+1;frame_red[frame_index]=frame_red[frame_index]+1;end
            if(error) errors=errors+1;
            if(sv) begin
                if(head>=tail || cv!==ev[head] || changed!==ec[head] || motion!==(ev[head] && ec[head]>=2))
                    $fatal(1,"grid frame=%0d cv=%0d count=%0d expected=%0d/%0d",head,cv,changed,ev[head],ec[head]);
                head=head+1;
            end
            checks=checks+1;
        end
    end
    task blank(input integer n);
        @(negedge clk);de=0;hs=1;
        repeat(n-1) @(negedge clk);
    endtask
    task boundary;
        blank(2);vs=1;
        repeat(2) @(negedge clk);
        vs=0;repeat(4) @(negedge clk);
    endtask
    task frame(input integer f,input integer malformed);
        integer diff,c,width,rows;
        begin
            boundary;frame_index=f;
            for(integer p=0;p<12;p=p+1) image[p]=80;
            if(f==1 || f==2) begin image[0]=120;image[11]=120;end
            if(f==5) image[11]=140;
            if(f==6 || f==7) for(integer p=0;p<12;p=p+1) image[p]=170;
            if(malformed==0) begin
                c=0;
                for(integer p=0;p<12;p=p+1) begin
                    diff=image[p]-previous[p];if(diff<0)diff=-diff;
                    if(history && diff>=24)c=c+1;
                    previous[p]=image[p];
                end
                ec[tail]=c;ev[tail]=history;tail=tail+1;history=1;
            end else history=0;
            rows=(malformed==2)?H+1:((malformed==3)?H-1:H);
            for(integer y=0;y<rows;y=y+1) begin
                width=(malformed==1 && y==3)?W-1:W;
                for(integer x=0;x<width;x=x+1) begin
                    @(negedge clk);de=1;hs=0;
                    gray=80;
                    if(x%2==0 && y%2==0 && y<H) gray=image[(y/2)*4+x/2];
                end
                blank(3);
            end
        end
    endtask
    initial begin
        for(integer p=0;p<12;p=p+1)previous[p]=0;
        for(integer p=0;p<16;p=p+1)frame_red[p]=0;
        repeat(3)@(negedge clk);rst_n=1;
        frame(0,0);frame(1,0);frame(2,0);frame(3,1);frame(4,0);frame(5,0);
        frame(6,0);frame(7,0);frame(8,2);frame(9,0);frame(10,3);frame(11,0);
        boundary;blank(8);
        if(head!=tail || head!=9 || errors<3 || red==0) $fatal(1,"coverage stats=%0d/%0d errors=%0d red=%0d",head,tail,errors,red);
        if(frame_red[2]!=24 || frame_red[3]==0 || frame_red[4]!=0) $fatal(1,"red border hold frame2=%0d frame3=%0d frame4=%0d",frame_red[2],frame_red[3],frame_red[4]);
        $display("PASS tb_video_motion_display cycles=%0d complete_frames=%0d format_errors=%0d red_pixels=%0d sampled_grid=4x3 invalid_width/extra_row/missing_row marker_alignment hold_frames=2",checks,head,errors,red);
        $finish;
    end
    initial begin #1000000;$fatal(1,"timeout");end
endmodule
