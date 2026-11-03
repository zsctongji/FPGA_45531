"""Expose existing pixel-domain ports in the plain wrapper, preserve protected IP."""
def patched(text):
 head,sep,tail=text.partition('endmodule');assert sep
 assert 'MIPI_CSI2_RX_PIXEL_SIDEBAND' not in head
 head=head.replace('`define MIPI_CSI2_RX_DEBUG','`define MIPI_CSI2_RX_DEBUG\n`define MIPI_CSI2_RX_PIXEL_SIDEBAND',1)
 old='    output [31:0] mipi_debug_out\n);'
 new='    output [31:0] mipi_debug_out,\n    output [15:0] pixel_wordcount,\n    output [5:0] pixel_datatype,\n    output [1:0] pixel_vc\n);'
 assert head.count(old)==1;head=head.replace(old,new)
 needle='    .pixel_data_valid ( pixel_data_valid ),';assert head.count(needle)==1
 head=head.replace(needle,needle+'\n    .pixel_wordcount ( pixel_wordcount ),\n    .pixel_datatype ( pixel_datatype ),\n    .pixel_vc ( pixel_vc ),')
 return head+sep+tail

def patched_bytes(data):
 head,sep,tail=data.partition(b'endmodule');assert sep
 # Only the public wrapper may be reserialized; keep every following byte.
 new_head=patched(head.decode('utf-8').replace('\r\n','\n')+'endmodule').encode('utf-8')
 return new_head+tail
