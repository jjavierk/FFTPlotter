# SerialPlotter

Serial plotter used to receive samples from the ADC.

The repo has been recently updated to show the actual sample rate of the data.
The accuracy of the measurement in about (Sample-rate) +- 0.1ksps.

The incomming packet has to be formated properly (otherwise it is discarted). The current format is:

 HEADER_A | HEADER_B | BYTE0 | BYTE2 ..... | BYTE9 | TAILER, 
 
where:
HEADER_A = 0x10, HEADER_B = 0x55, TAILER = 0xAA
