I got the line out of an E-Piano hooked into a USB sound card. 

The script opens the device as an input stream and measures the incoming audios loudness indefinitely to compare against the set threshold.

If the loudness threshold is not met, the script stays in stand by and drops incoming data.
If there is audible sound incoming for a while, it starts dumping the data to a newly generated file until it's silent for another while.
It then returns to stand by and normalizes the new file.
