from epics import caget, caput, cainfo
import epics
import time

# get the required PV
campv = epics.PV('1idPG2:cam1:TriggerMode')
counterpv = epics.PV('1idPG2:cam1:NumImagesCounter_RBV')

flag = 1
seq = 0

while flag is 1:  
    i = 0 
    while campv.get() == 3: 
        # start monitor counter during FlyScan
        counter = counterpv.get() 
        t0 = time.time()
        bad_scan = 0
        if i == 0: 
            print(f'Fly scan {seq: 4d} has started, {counter} images collected') 
        i += 1 
        time.sleep(5) 
        while (counterpv.get() - counter) == 0 and campv.get() == 3:
			duration = time.time()-t0
            print(f'Fly scan {seq: 4d} failed, image counter stucked at {counter} images for {duration} seconds')
            if duration > 60:
				bad_scan = 1
				print(f'Sending internal trigger to abort scan {seq: 4d}')
				campv.put(0)
			if bad_scan == 1:
				time.sleep((1801-counter)/18+5)
			else:
				time.sleep(30)
    print(f'Fly scan {seq:4d} has finished, moving to next step...') 
    seq += 1 
    time.sleep(66)
