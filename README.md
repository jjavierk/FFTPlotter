# FFT ploter

FFT plotter used to receive samples from an STM32F407-DISC (main.c)

Now, it also includes a spectrogram (spectro.py)


For these apps to work, the incoming packet must be properly formatted (otherwise it is discarded). The current format is:

 HEADER_A | HEADER_B | BYTE0 | BYTE2 ..... | BYTE_N | TAILER, 
 
where:
HEADER_A = 0x10, HEADER_B = 0x55, TAILER = 0xAA
