from .controller import LovenseController, Toy

__version__ = '1.0.0'

def create_controller(short_code,anonkey=None,on_connect_callback=None):
    """
    Create and start a Lovense controller with the given short code.
    
    Args:
        short_code (str): The Lovense control link short code
    
    Returns:
        LovenseController: The initialized controller instance
    """
    controller = LovenseController(short_code,anonkey,on_connect_callback)
    controller.start()
    return controller

__all__ = ['LovenseController', 'Toy', 'create_controller']