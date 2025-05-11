# lovepy

Example Code
```
import time
from lovepy import LovenseController, Toy

def on_connect():
    print("Successfully connected to the toy!")

def on_disconnect():
    print("Disconnected from the toy.")

controller = LovenseController(short_code="<SHORTCODE>", on_connect_callback=on_connect, on_disconnect_callback=on_disconnect)

if controller.start():
    print("Controller started successfully!")
    
    time.sleep(1)
    
    toys = controller.get_toys()
    
    if toys:
        print(f"Found {len(toys)} toy(s):")
        for toy in toys:
            print(toy)
        
        for toy in toys:
            controller.set_strength(toy, 20)
        
        time.sleep(1)
    
    controller.stop()
else:
    print("Failed to connect to the controller.")
```
