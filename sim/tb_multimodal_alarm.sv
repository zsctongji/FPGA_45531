`timescale 1ns/1ps
module tb_multimodal_alarm;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, snapshot=0, armed=1, ack=0, vv=1,tv=1,ev=1;
    reg [31:0] now_ms=0,vt=0,tt=0,et=0;
    reg [7:0] vs=255,ts=255,es=255;
    reg moving=1,person=1,thermal=1;
    wire rv,fault,duplicate,alarm,event_valid,led,buzzer,border;
    wire [7:0] score;
    wire [3:0] alarm_type;wire[7:0] alarm_confidence;wire[31:0]event_time;
    integer checks=0, events=0;
    multimodal_alarm #(.VISUAL_MAX_AGE_MS(100),.THERMAL_MAX_AGE_MS(50),.ENV_MAX_AGE_MS(200),.HOLD_MS(300)) dut(
        .clk(clk),.rst_n(rst_n),.now_ms(now_ms),.snapshot_valid(snapshot),.armed(armed),.acknowledge(ack),
        .visual_valid(vv),.thermal_valid(tv),.environment_valid(ev),
        .visual_timestamp_ms(vt),.thermal_timestamp_ms(tt),.environment_timestamp_ms(et),
        .visual_score(vs),.thermal_score(ts),.environment_score(es),
        .motion_detected(moving),.person_detected(person),.thermal_presence(thermal),
        .result_valid(rv),.data_fault(fault),.duplicate_frame(duplicate),.fused_score(score),
        .alarm_active(alarm),.event_valid(event_valid),.alarm_type(alarm_type),.alarm_confidence(alarm_confidence),.event_timestamp_ms(event_time),
        .led_request(led),.buzzer_request(buzzer),.red_border_request(border));
    task tick;
        @(posedge clk); #2;
        if({led,buzzer,border} !== {3{alarm}}) $fatal(1,"alarm output enables disagree");
        if(alarm_type !== (alarm?4'd1:4'd0))$fatal(1,"event type");
        if(event_valid) events=events+1;
        checks=checks+1;
        @(negedge clk);
    endtask
    task sample(input reg [31:0] time_ms);
        now_ms=time_ms; vt=time_ms; tt=time_ms; et=time_ms; snapshot=1; tick;
    endtask
    task reset;
        rst_n=0; snapshot=0; tick; rst_n=1; tick;
    endtask
    initial begin
        @(negedge clk); reset;
        sample(1000); if(!rv || alarm || score!=255) $fatal(1,"first confirmation/max score");
        tick; if(!duplicate || alarm) $fatal(1,"duplicate counted twice");
        sample(1020); if(!alarm || !event_valid) $fatal(1,"second distinct frame should trigger");
        if(alarm_confidence!=255 || event_time!=1020)$fatal(1,"event payload");
        sample(1040); if(!alarm || event_valid) $fatal(1,"repeated trigger must not spam events");
        vs=100;ts=200;es=0;sample(1050);
        if(!alarm || score!=110 || alarm_confidence!=255 || event_time!=1020)$fatal(1,"event confidence must retain accepted trigger");
        vs=255;ts=255;es=255;
        snapshot=0; now_ms=1339; tick; if(!alarm) $fatal(1,"hold too short");
        now_ms=1340; tick; if(alarm) $fatal(1,"hold expiry independent of new data");
        sample(2000); if(alarm) $fatal(1,"long frame gap must restart confirmation");
        sample(2020); if(!alarm) $fatal(1,"restart confirmation");
        ack=1; tick; if(alarm) $fatal(1,"acknowledge clear");
        ack=0; tick; if(!duplicate || alarm) $fatal(1,"acknowledged snapshot retrigger");
        sample(2040); if(alarm) $fatal(1,"first frame after ack");
        sample(2060); if(!alarm) $fatal(1,"second frame after ack");
        armed=0; tick; if(alarm) $fatal(1,"disarm"); armed=1;
        // Weighted score: (60*100 + 25*200 + 15*0)/100 = 110.
        vs=100;ts=200;es=0;sample(2080); if(!rv || score!=110 || alarm) $fatal(1,"score arithmetic/threshold");
        vs=255;ts=255;es=255;
        sample(2100); if(alarm) $fatal(1,"new confirmation after low score");
        now_ms=2120;vt=2120;tt=2069;et=2120;tick;
        if(!fault || rv) $fatal(1,"thermal stale age 51");
        sample(2140); if(alarm) $fatal(1,"bad sample must break confirmation");
        now_ms=2160;vt=2160;tt=2110;et=1960;tick; // Inclusive boundary ages 50/200.
        if(!rv || !alarm) $fatal(1,"inclusive freshness limits");
        armed=0;tick;armed=1;
        now_ms=2180;vt=2180;tt=2181;et=2180;tick;
        if(!fault || rv) $fatal(1,"future sensor timestamp");
        tv=0;sample(2200);if(!fault) $fatal(1,"missing thermal");tv=1;
        ev=0;sample(2220);if(!fault) $fatal(1,"missing environment");ev=1;
        vv=0;sample(2240);if(!fault) $fatal(1,"missing vision");vv=1;
        now_ms=2401;vt=2300;tt=2401;et=2401;tick;
        if(!fault) $fatal(1,"stale visual");
        sample(2420); sample(2440);if(!alarm) $fatal(1,"recovery after missing sources");
        // Old frames must not update the confidence nor become a new event.
        now_ms=2450;vt=2430;tt=2450;et=2450;vs=0;tick;
        if(!duplicate || rv || score!=255) $fatal(1,"out of order frame");vs=255;
        reset;
        sample(32'hfffffff0); if(alarm) $fatal(1,"rollover first");
        sample(32'h00000004); if(!alarm || !event_valid) $fatal(1,"timestamp rollover");
        snapshot=0;now_ms=32'h00000130;tick;if(alarm) $fatal(1,"rollover expiry");
        reset;person=0;sample(100);sample(120);if(alarm) $fatal(1,"non-person must not alarm");
        person=1;thermal=0;sample(140);sample(160);if(alarm) $fatal(1,"no thermal presence");
        thermal=1;moving=0;sample(180);sample(200);if(alarm) $fatal(1,"no motion");
        moving=1;sample(220);sample(240);if(!alarm) $fatal(1,"presence gates recovery");
        $display("PASS tb_multimodal_alarm checks=%0d events=%0d weighted_score freshness future missing duplicate order rollover confirm hold ack disarm",checks,events);
        $finish;
    end
    initial begin #100000; $fatal(1,"timeout"); end
endmodule
