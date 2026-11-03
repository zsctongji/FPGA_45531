"""Diagnostic Pack40-only profile; RAW10 retained, other pack classes disabled."""
from patch_c9_sideband_vendor import patched_bytes as expose_sideband
def patched_bytes(data):
 expanded=expose_sideband(data);head,sep,tail=expanded.partition(b'endmodule')
 old=b'.PACK_TYPE (15)';assert head.count(old)==1
 return head.replace(old,b'.PACK_TYPE (1)')+sep+tail
def patched(text):return patched_bytes(text.encode('utf-8')).decode('utf-8')
