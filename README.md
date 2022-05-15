# FFT ploter

Serial plotter used to receive samples from and STM32F407-DISC.


The incomming packet has to be formated properly (otherwise it is discarted). The current format is:

 HEADER_A | HEADER_B | BYTE0 | BYTE2 ..... | BYTE_N | TAILER, 
 
where:
HEADER_A = 0x10, HEADER_B = 0x55, TAILER = 0xAA
