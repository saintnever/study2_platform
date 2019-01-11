import subprocess
import blob
C_SHARP_EXECUTABLE_FILE_PATH = \
    "C:/Users/saintnever/Documents/THU_drive/autoID/mercuryapi-1.31.0.33/cs/Samples/Demo/bin/Debug/Demo.exe tmr://101.6.114.16 read-async"
i= 0
p = subprocess.Popen(C_SHARP_EXECUTABLE_FILE_PATH, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                     stderr=subprocess.PIPE)

while i < 1000:
    line = p.stdout.readline()
    # out, err = p.communicate()
    # p.kill()
    i += 1
    print(line)