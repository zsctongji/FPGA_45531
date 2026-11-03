"""Private plain I2C wrapper/ROM patch; publish helper only, not vendor sources."""
import re
def patched(name,text):
 if name=='i2c_master_reg_rom.v':
  old="ROM[8'h92] = {16'h0100,8'h01,1'b0};";assert text.count(old)==1
  text=text.replace(old,"ROM[8'h92] = {16'h0100,8'h00,1'b0};")
  last="ROM[8'hb5] = {16'h37f9,8'h00,1'b1};";assert text.count(last)==1
  return text.replace(last,last+"\nROM[8'hb6] = {16'h0100,8'h01,1'b0};")
 if name=='i2c_master_reg_set.v':
  text,n=re.subn(r'(input\s+wire\s+rst_n\s*,)',r'\1\n input wire allow_stream,',text,count=1);assert n==1
  text,n=re.subn(r'if\(\s*cnt\s*<\s*DATA_LENGTH\s*\)', 'if(cnt < DATA_LENGTH && (cnt != DATA_LENGTH-1 || allow_stream))',text);assert n==1
  return text
 if name=='i2c_master_ctrl_top.v':
  text,n=re.subn(r'(input\s+wire\s+rst_n\s*,)',r'\1\n input wire allow_stream,',text,count=1);assert n==1
  text,n=re.subn(r'parameter DATA_LENGTH\s*=\s*182','parameter DATA_LENGTH = 183',text);assert n==1
  a=text.index(') u_reg_set(') if ') u_reg_set(' in text else text.index(')u_reg_set(');b=text.index(');',a)
  part=text[a:b];part,n=re.subn(r'(\.rst_n\s*\(rst_n\)\s*,)',r'\1\n .allow_stream(stream_sync[1]),',part);assert n==1
  text=text[:a]+part+text[b:]
  pos=text.index(');')+2
  sync='\n(* async_reg="true" *) reg [1:0] stream_sync;\nalways @(posedge clk or negedge rst_n)\n if(!rst_n)stream_sync<=0;else stream_sync<={stream_sync[0],allow_stream};\n'
  return text[:pos]+sync+text[pos:]
 raise ValueError(name)
