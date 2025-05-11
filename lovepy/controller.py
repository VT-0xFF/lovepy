import requests
import socketio
import time
import json
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import uuid
import threading

class Toy:
    """Class representing a Lovense toy"""
    def __init__(self, toy_data):
        self.type = toy_data.get("type", "")
        self.is_control = toy_data.get("isControl", None)
        self.version = toy_data.get("version", "")
        self.name = toy_data.get("name", "")
        self.status = toy_data.get("status", "false")
        self.battery = toy_data.get("battery", None)
        self.id = toy_data.get("id", "")
        self.device_type = toy_data.get("deviceType", "")
        self.toy_fun = toy_data.get("toyFun", "")
        self.work_mode = toy_data.get("workMode", None)
        self.toy_data = toy_data

    def __str__(self):
        return f"Toy(\ntype={self.type}, id={self.id}, name={self.name}, \nis_control={self.is_control}, version={self.version}, status={self.status}, \nbattery={self.battery}, device_type={self.device_type}, \ntoy_fun={self.toy_fun}, work_mode={self.work_mode})\ntoy_data= {json.dumps(self.toy_data)}"

class LovenseController:
    """
    A controller for Lovense devices using their anonymous control link API.
    
    Args:
        short_code (str): The short code for the Lovense control link
    """
    
    def __init__(self, short_code, anon_key=None, on_connect_callback=None):
        self.short_code = short_code
        self.session = requests.Session()
        self.anon_key = anon_key
        self.link_id = None
        self.ws_url = None
        self.controlLinkData = None
        self.aes_keys = {"x": "", "y": ""}
        self.sio = socketio.Client()
        self.running = False
        self.msg_id = ""
        self.last_strengths = {}
        self.connected = False
        self.message_callbacks = []
        self.on_connect_callback = on_connect_callback
        self.on_disconnect_callback = None
        self._setup_socket_handlers()
        self.ping_thread = None

    def _aes_encrypt_xy(self, word):
        """Encrypt a string using AES CBC mode with stored keys"""
        try:
            key = self.aes_keys["x"].encode('utf-8')
            iv = self.aes_keys["y"].encode('utf-8')
            key = pad(key, 16)[:16]
            iv = pad(iv, 16)[:16]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            padded_text = pad(word.encode('utf-8'), AES.block_size)
            encrypted = cipher.encrypt(padded_text)
            return base64.b64encode(encrypted).decode('utf-8')
        except:
            return word

    def _aes_decrypt_xy(self, word):
        """Decrypt a string using AES CBC mode with stored keys"""
        try:
            key = self.aes_keys["x"].encode('utf-8')
            iv = self.aes_keys["y"].encode('utf-8')
            key = pad(key, 16)[:16]
            iv = pad(iv, 16)[:16]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            encrypted_data = base64.b64decode(word)
            decrypted_padded = cipher.decrypt(encrypted_data)
            decrypted = unpad(decrypted_padded, AES.block_size)
            return decrypted.decode('utf-8')
        except:
            return word


    def _start_ping_loop(self):
        def ping():
            while self.running and self.connected:
                try:
                    self.sio.eio.send("2")
                except Exception as e:
                    print(f"Ping error: {e}")
                time.sleep(10)
        self.ping_thread = threading.Thread(target=ping, daemon=True)
        self.ping_thread.start()


    def _init_connection(self):
        url = "https://c.lovense-api.com/anon/longtimecontrollink/init"
        data = {"shortCode": self.short_code}
        if self.anon_key:
            data["anon_key"] = self.anon_key
        response = self.session.post(url, data=data)
        if response.status_code == 200:
            result = response.json()
            if result["result"]:
                self.anon_key = result["data"]["anonKey"]
                self.link_id = result["data"]["id"]
                return True
        return False
        
    def register_message_callback(self, callback):
        self.message_callbacks.append(callback)
        
    def set_on_connect_callback(self, callback):
        self.on_connect_callback = callback
        
    def set_on_disconnect_callback(self, callback):
        self.on_disconnect_callback = callback
        
    def _check_status(self):
        url = "https://c.lovense-api.com/anon/controllink/status"
        data = {"id": self.link_id, "historyUrl": ""}
        response = self.session.post(url, data=data)
        if response.status_code == 200 and response.json()["result"]:
            return True
        return False
    
    def _join_control(self):
        url = "https://c.lovense-api.com/anon/controllink/join"
        data = {"id": self.link_id, "historyUrl": ""}
        response = self.session.post(url, data=data)
        if response.status_code == 200:
            result = response.json()
            if result["result"]:
                self.ws_url = result["data"]["wsUrl"].replace("https", "wss")
                self.controlLinkData = result["data"]["controlLinkData"]
                self.aes_keys = {"x": self.controlLinkData["x"], "y": self.controlLinkData["y"]}
                return True
        return False

    def get_toys(self):
        """
        Get a list of all connected toys.
        
        Returns:
            list: List of Toy objects representing connected toys, empty list if not connected
        """
        if not self.connected or not self.controlLinkData:
            return []
        return [Toy(toy_data) for toy_data in self.controlLinkData["creator"]["toys"]]

    def set_strength(self, toy, strength_value):
        """
        Set the strength value for a specific toy.
        
        Args:
            toy (Toy): The Toy object to control
            strength_value (int or dict): Strength value between 0 and 20, or a dict of values
        """
        if not self.running or not self.connected or not isinstance(toy, Toy):
            return False

        toy_id = toy.id
        if toy_id not in self.last_strengths:
            self.last_strengths[toy_id] = None

        if self.last_strengths[toy_id] == strength_value:
            return False

        keys = ["v", "v1", "v2", "v3", "s", "p", "r", "f", "t", "d", "o", "pos"]

        if isinstance(strength_value, int):
            strength_value = max(0, min(20, strength_value))
            strength_dict = {k: strength_value for k in keys}
        elif isinstance(strength_value, dict):
            strength_dict = {k: strength_value.get(k, -1) for k in keys}
        else:
            return False  # Invalid input type

        self.last_strengths[toy_id] = strength_value

        id_obj = {
            toy_id: strength_dict
        }

        command_json = {
            "version": 5,
            "cate": "id",
            "id": id_obj
        }

        self.sio.emit("anon_command_link_ts", {
            "toyCommandJson": json.dumps(command_json),
            "linkId": self.controlLinkData["linkId"],
            "userTouch": (isinstance(strength_value, dict) and any(v < 0 for v in strength_dict.values()))
        })
        return True

    def chat(self, message):
        """
        Send a chat message to the Lovense control link creator.
        
        Args:
            message (str): The message to send
        """
        if not self.running or not self.connected or not self.controlLinkData:
            return False
        
        self.sio.emit("q_send_im_msg_ts", {
            "ackId": str(uuid.uuid4()),
            "dateImType": "control_link",
            "dateImTypeData": self.link_id,
            "msgData": self._aes_encrypt_xy(json.dumps({
                "msgId": "1",
                "text": message
            })),
            "msgType": "chat",
            "msgVer": 8,
            "toId": self.controlLinkData["creator"]["userId"]
        })
        return True
        
    def send(self, title, content):
        """
        Send a message to the Lovense control link.
        
        Args:
            title (str): The code to send
            content (dict): The data to send
        """
        if not self.running or not self.connected or not self.controlLinkData:
            return False
        
        self.sio.emit(title, content)
        return True
        
    def close(self):
        if not self.running or not self.connected or not self.controlLinkData:
            return False
        
        self.sio.emit("anon_end_control_link_ts", {"linkId": self.link_id})
        return True

    def _setup_socket_handlers(self):
        @self.sio.event
        def connect():
            self.connected = True
            self.running = True
            self.sio.emit("anon_open_control_panel_ts", {"linkId": self.link_id})
            if self.on_connect_callback:
                self.on_connect_callback()
            self._start_ping_loop()

        @self.sio.event
        def disconnect():
            self.running = False
            self.connected = False
            if self.on_disconnect_callback:
                self.on_disconnect_callback()

        @self.sio.event
        def anon_link_is_end_tc(data):
            """try:
                self.stop()
            except:
                pass"""
            print(json.dumps(data, indent=4))
            if self.on_disconnect_callback:
                self.on_disconnect_callback()

        @self.sio.event
        def q_you_have_some_new_im_msg_tc(data):
            msg_request = {
                "dateImTypeData": self.link_id,
                "msgId": self.msg_id,
                "ackId": ""
            }
            self.send("q_get_user_new_msg_list_ts", msg_request)

        @self.sio.event
        def q_ack_user_new_msg_list_tc(data):
            message_list = data.get("list", [])
            self.msg_id = message_list[-1].get("msgId")
            for message in message_list:
                msg_type = message.get("msgType")
                msg_data = message.get("msgData")
                
                if msg_type and msg_data:
                    decrypted = self._aes_decrypt_xy(msg_data)
                    try:
                        result = json.loads(decrypted)
                        
                        message_data = {
                            "type": msg_type,
                            "content": result
                        }
                        
                        if msg_type == "audio":
                            audio_url = "https://cdn.lovense-api.com" + result.get("url", "")
                            try:
                                current_time = int(time.time())
                                audio_filename = f"audios/{current_time}_{self.short_code}.mp3"
                                
                                if not os.path.exists("audios"):
                                    os.makedirs("audios")
                                    
                                response = requests.get(audio_url)
                                if response.status_code == 200:
                                    with open(audio_filename, "wb") as f:
                                        f.write(response.content)
                                    message_data["audio_path"] = audio_filename
                                else:
                                    message_data["error"] = f"Download failed: Status {response.status_code}"
                            except Exception as e:
                                message_data["error"] = str(e)
                        for callback in self.message_callbacks:
                            try:
                                callback(message_data)
                            except Exception as e:
                                print(f"Callback error: {str(e)}")
                                
                    except json.JSONDecodeError:
                        error_data = {
                            "type": "error",
                            "content": "Failed to decode message"
                        }
                        for callback in self.message_callbacks:
                            callback(error_data)

    def start(self):
        """
        Start the Lovense controller.
        
        Returns:
            bool: True if successfully started, False otherwise
        """
        if self._init_connection():
            if self._check_status():
                if self._join_control():
                    try:
                        self.sio.connect(
                            self.ws_url,
                            transports=['websocket'],
                            socketio_path='/anon.io'
                        )
                        return True
                    except:
                        self.running = False
                        self.connected = False
                        return False
        return False

    def stop(self):
        self.running = False
        self.connected = False
        self.sio.disconnect()

    def is_running(self):
        return self.running and self.connected