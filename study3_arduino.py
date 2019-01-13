from pyfirmata import ArduinoMega, util
import time
import pyfirmata
board = ArduinoMega('/dev/tty.usbmodem1441')
#board = ArduinoMega('COM8')
board.analog[0].mode = pyfirmata.INPUT
it = util.Iterator(board)
it.start()
board.analog[0].enable_reporting()
while True : 
	print(board.analog[0].read())