"""Private override: consume the existing SPI input sample hold register.
The generated vendor file is never changed. Seven mux inputs in the SPI engine
used raw pins despite the delayed readFill/readDone strobes. Use the register
already captured by that engine, keeping command timing and public ABI intact.
"""
import re
MODULE='TopLevel_ba6762f3781649428952cf46a6343376'
def patch(text):
 match=re.search(r'module '+MODULE+r' \(.*?\nendmodule',text,re.S)
 if not match:raise ValueError('Pinned SPI module not found')
 original=match.group()
 fixed,n=re.subn(r'(assign _zz_inputPhy_dataRead(?:_\d+)? = )\{io_spi_data_3_read\[0\],\{io_spi_data_2_read\[0\],\{io_spi_data_1_read\[0\],io_spi_data_0_read\[0\]\}\}\};',r'\1inputPhy_dataReadBuffer;',original)
 if n!=7:raise ValueError('Expected exactly seven raw SPI mux inputs')
 return text[:match.start()]+fixed+text[match.end():]
