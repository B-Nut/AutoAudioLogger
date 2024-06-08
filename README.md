I got the line out of an E-Piano hooked into a USB sound card. 

The script opens the device as an input stream and measures the incoming loudness indefinitely to compare against a set threshold.
- If the loudness threshold is not met, the script stays in stand by: It retains the specified intervals of silence, but drops anything older.
- If there is a loud sound interval incoming, it starts caching the audio.
- After a set amount of loud intervals, the data is written to a newly generated file.
- While caching or recording, prolonged silence after the specified retain intervals is dropped.
- Recording to the same file can continue, before the recorder goes back to stand by.
- After a set amount of silent intervals in a row, the caching or recording stops and the script goes to stand by.
- When the script goes to stand by and a file gets closed, the script normalizes the wave file.
