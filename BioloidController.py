#!/usr/bin/env python

from stm_uart_bus import UART_Bus
import pyb
import struct

BIOLOID_SHIFT = 3
BIOLOID_FRAME_LENGTH = 33

AX_GOAL_POSITION = 30
AX_READ_DATA = 2
AX_WRITE_DATA = 3
AX_SYNC_WRITE = 131

class BioloidController:

    def __init__(self):
        self.id = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        self.pose = [512, 512, 512, 512, 512, 512, 512, 512, 512, 512, 512, 512]
        self.nextPose = [512, 512, 512, 512, 512, 512, 512, 512, 512, 512, 512, 512]
        self.speed = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.interpolating = False
        self.playing = False
        self.servoCount = 12
        self.lastFrame = pyb.millis()
        self.serialPort = UART_Bus(1, 1000000, show_packets=False)

    # Load a pose into nextPose
    def loadPose(self, poseArray):
        for i in range(self.servoCount):
            self.nextPose[i] = (poseArray[i]) # << BIOLOID_SHIFT)
            #print ('loadPose[', self.id[i], '] = ', self.nextPose[i])

    # read the current robot's pose
    def readPose(self):
        for i in range(self.servoCount):
            self.pose[i] = (self.readTwoByteRegister(self.id[i], AX_GOAL_POSITION)) # << BIOLOID_SHIFT)
            #print ('readPose[', self.id[i], '] = ', self.pose[i])
            pyb.delay(25)

    def writePose(self):
        values = []
        for i in range(self.servoCount):
            values.append(struct.pack('<H', int(self.pose[i])))
            #print ("SYNC_WRITE ", self.id[i], " - ", int(self.pose[i]))
        self.serialPort.sync_write(self.id, AX_GOAL_POSITION, values)

    def setPosition(self, deviceId, position):
        self.writeData(deviceId, AX_GOAL_POSITION, struct.pack('<H', position))

    def writeData(self, deviceId, controlTableIndex, byteData):
        return self.serialPort.write(deviceId, controlTableIndex, byteData)

    def readTwoByteRegister(self, deviceId, controlTableIndex):
        values = self.serialPort.read(deviceId, controlTableIndex, 2)
        return struct.unpack('<H', values)[0]

    def readOneByteRegister(self, deviceId, controlTableIndex):
        values = self.serialPort.read(deviceId, controlTableIndex, 1)
        return struct.unpack('B', values)[0]

    def readData(self, deviceId, controlTableIndex, count):
        return self.serialPort.read(deviceId, controlTableIndex, count)

    def interpolateSetup(self, time):
        frames = (time / BIOLOID_FRAME_LENGTH) + 1
        self.lastFrame = pyb.millis()
        for i in range(self.servoCount):
            if self.nextPose[i] > self.pose[i]:
                self.speed[i] = (self.nextPose[i] - self.pose[i]) / frames + 1
            else:
                self.speed[i] = (self.pose[i] - self.nextPose[i]) / frames + 1
        self.interpolating = True

    def interpolateStep(self):
        if not self.interpolating:
            return
        complete = self.servoCount
        while (pyb.millis() - self.lastFrame < BIOLOID_FRAME_LENGTH):
            pass
        self.lastFrame = pyb.millis()
        for i in range(self.servoCount):
            diff = self.nextPose[i] - self.pose[i]
            if diff == 0:
                complete -= 1
            else:
                if diff > 0:
                    if diff < self.speed[i]:
                        self.pose[i] = self.nextPose[i]
                        complete -= 1
                    else:
                        self.pose[i] += self.speed[i]
                else:
                    if (-diff) < self.speed[i]:
                        self.pose[i] = self.nextPose[i]
                        complete -= 1
                    else:
                        self.pose[i] -= self.speed[i]
        if complete <= 0:
            self.interpolating = False
        self.writePose()


#============================================================

