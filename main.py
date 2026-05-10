from micropython import const
import framebuf
from machine import Pin, SoftI2C, SPI
import time
import utime
import os
from mfrc522 import MFRC522
from keypad import Keypad
import _thread
import st7789
import vga1_bold_16x32 as font



class Game:
    def __init__(self):
        self.COLOR_BG = st7789.color565(20, 120, 40)
        self.players = [1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500]
        self.players_rfid = {"36046426852801050": 0, "36046426852800790": 1, "36046426852800540": 2, "36046426852800280": 3, "36046426852800020": 4, "36046426852799770": 5, "36046426852799510": 6, "36046426852799260": 7}
        
        self.load_from_file()
        
        self.state_game = "" # "" "plus1" "plus2" "minus1" "minus2" "trade1" "trade2" "trade3" "trade4"
        self.number = ""
        
        # Oled
        self.BACKLIGHT_PIN = 21
        self.RESET_PIN = 20
        self.DC_PIN = 12
        self.CS_PIN = 1
        self.CLK_PIN = 2
        self.DIN_PIN = 3

        self.spi = SPI(0, baudrate=31250000, sck=Pin(self.CLK_PIN), mosi=Pin(self.DIN_PIN))
        self.oled_width = 240
        self.oled_height = 320
        self.tft = st7789.ST7789(self.spi, self.oled_width, self.oled_height,
            reset=Pin(self.RESET_PIN, Pin.OUT),
            cs=Pin(self.CS_PIN, Pin.OUT),
            dc=Pin(self.DC_PIN, Pin.OUT),
            backlight=Pin(self.BACKLIGHT_PIN, Pin.OUT),
            rotation=4)
        self.tft.init()

        # RFID
        self.rfid_reader = MFRC522(spi_id=1, sck=10, miso=8, mosi=11, cs=9, rst=22)
        self.rfid_reader.init()

        # Keypad
        # Define GPIO pins for rows
        self.row_pins = [Pin(0),Pin(4),Pin(5),Pin(6)]
        # Define GPIO pins for columns
        self.column_pins = [Pin(7),Pin(13),Pin(14),Pin(15)]
        # Define keypad layout
        self.keys = [
            ['1', '2', '3', 'A'],
            ['4', '5', '6', 'B'],
            ['7', '8', '9', 'C'],
            ['*', '0', '#', 'D']]

        self.keypad = Keypad(self.row_pins, self.column_pins, self.keys)
        

    def replace_rfid_by_index(self, target_index, new_rfid):
        for rfid, index in self.players_rfid.items():
            if index == target_index:
                del self.players_rfid[rfid]
                self.players_rfid[new_rfid] = target_index
                break
    def load_from_file(self):
        try:
            with open('save.txt', 'r') as f:
                for i in range(0, 8):
                    self.players[i] = int((f.readline())[:-1])
                self.players_rfid = {}
                for i in range(0, 8):
                    self.players_rfid[(f.readline())[:-1]] = i
        except:
            with open('save.txt', 'w') as f:
                for i in range(0, 7):
                    f.write('1500\n')
                    self.players[i] = 1500

            players_sorted = sorted(self.players_rfid.items(), key=lambda x: x[1])
            with open('save.txt', 'a') as f:
                for rfid, index in players_sorted:
                    f.write(f"{rfid}\n")
    
    def save_to_file(self):
        with open('save.txt', 'w') as f:
            for i in range(0, 8):
                f.write(f"{self.players[i]}\n")

        players_sorted = sorted(self.players_rfid.items(), key=lambda x: x[1])
        with open('save.txt', 'a') as f:
            for rfid, index in players_sorted:
                f.write(f"{rfid}\n")
                
    def keypad_thread(self):
        state = False
        while True:
            key_pressed = self.keypad.read_keypad()
            if (key_pressed != None) and (state == False):
                if key_pressed == "D": #trade
                    if self.state_game == "trade1" and len(self.number) > 0:
                        self.number = self.number[:-1]
                        self.show_trade(self.number)
                    if self.state_game == "minus1" and len(self.number) > 0:
                        self.number = self.number[:-1]
                        self.show_minus(self.number)
                    if self.state_game == "plus1" and len(self.number) > 0:
                        self.number = self.number[:-1]
                        self.show_plus(self.number)
                if key_pressed == "B": #trade
                    self.number = ""
                    self.state_game = "trade1"
                    self.show_trade(self.number)
                if key_pressed == "C": #break
                    self.show_score_all()
                    self.state_game = ""
                    self.number = ""
                if key_pressed == "#": #minus
                    self.number = ""
                    self.state_game = "minus1"
                    self.show_minus(self.number)
                if key_pressed == "*": #plus
                    self.number = ""
                    self.state_game = "plus1"
                    self.show_plus(self.number)
                if key_pressed in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
                    if self.state_game == "plus1" and len(self.number) < 5:
                        self.number = self.number + key_pressed
                        self.show_plus(self.number)
                    if self.state_game == "minus1" and len(self.number) < 5:
                        self.number = self.number + key_pressed
                        self.show_minus(self.number)
                    if self.state_game == "trade1" and len(self.number) < 5:
                        self.number = self.number + key_pressed
                        self.show_trade(self.number)
                    if self.state_game == "setRfid":
                        self.number = key_pressed
                        self.tft.text(font, f"{self.number}", 80, 100, st7789.color565(255,255,255), self.COLOR_BG)
                if key_pressed == "A": #approve
                    if self.state_game == "setRfid":
                        if self.number in ("1", "2", "3", "4", "5", "6", "7", "8"):
                            self.state_game = ""
                            self.replace_rfid_by_index(int(self.number)-1, self.save_rfid)
                            self.save_to_file()
                            self.load_from_file()
                            self.show_score_all()
                    if self.state_game == "plus1":
                        if self.number != "":
                            self.state_game = "plus2"
                            self.number = self.number + "A"
                            self.show_plus(self.number)
                        else:
                            self.show_score_all()
                            self.state_game = ""
                            self.number = ""
                    if self.state_game == "minus1":
                        if self.number != "":
                            self.state_game = "minus2"
                            self.number = self.number + "A"
                            self.show_minus(self.number)
                        else:
                            self.show_score_all()
                            self.state_game = ""
                            self.number = ""
                    if self.state_game == "trade1":
                        if self.number != "":
                            self.state_game = "trade2"
                            self.number = self.number + "A"
                            self.show_trade(self.number)
                            #restore game
                            if self.number == "99123A":
                                self.players = [1500]*8
                                self.save_to_file()
                                self.number = ""
                                self.state_game = ""
                                self.show_score_all()
                            elif self.number == "99124A":
                                self.players = [1500]*8
                                self.players_rfid = {"36046426852801050": 0, "36046426852800790": 1, "36046426852800540": 2, "36046426852800280": 3, "36046426852800020": 4, "36046426852799770": 5, "36046426852799510": 6, "36046426852799260": 7}
                                self.save_to_file()
                                self.load_from_file()
                                self.number = ""
                                self.state_game = ""
                                self.show_score_all()
                        else:
                            self.show_score_all()
                            self.state_game = ""
                            self.number = ""
                    
                state = True
            elif key_pressed == None:
                state = False

    def run_game(self):
        _thread.start_new_thread(self.keypad_thread, ())
        self.show_score_all()
        while True:
            (card_status, tag_type) = self.rfid_reader.request(self.rfid_reader.REQIDL)
            if card_status == self.rfid_reader.OK:
                (card_status, card_id) = self.rfid_reader.SelectTagSN()
                if card_status == self.rfid_reader.OK:
                    rfid_card = str(int.from_bytes(bytes(card_id),"little",False))
                    if rfid_card in self.players_rfid.keys():
                        player_id = self.players_rfid[rfid_card]
                        if self.state_game == "plus2":
                            self.players[player_id] = self.players[player_id] + int(self.number[:-1])
                            self.save_to_file()
                            self.state_game = ""
                            self.number = ""
                            self.show_score_one(player_id)
                        elif self.state_game == "minus2":
                            if (self.players[player_id] - int(self.number[:-1])) >= 0:
                                self.players[player_id] = self.players[player_id] - int(self.number[:-1])
                                self.save_to_file()
                                self.state_game = ""
                                self.number = ""
                                self.show_score_one(player_id)
                            else:
                                self.show_not_enough(self.players[player_id] - int(self.number[:-1]))
                                self.state_game = ""
                                self.number = ""
                        elif self.state_game == "trade2":
                            if (self.players[player_id] - int(self.number[:-1])) >= 0:
                                self.save_player_id_trade = player_id
                                self.show_score_one_number((self.players[player_id] - int(self.number[:-1])))
                                self.state_game = "trade3"
                            else:
                                self.show_not_enough(self.players[player_id] - int(self.number[:-1]))
                                self.state_game = ""
                                self.number = ""
                        elif self.state_game == "trade3":
                            self.players[self.save_player_id_trade] = self.players[self.save_player_id_trade] - int(self.number[:-1])
                            self.players[player_id] = self.players[player_id] + int(self.number[:-1])
                            self.save_to_file()
                            self.state_game = ""
                            self.number = ""
                            self.show_score_one(player_id)
                            self.save_player_id_trade = -1
                        else:
                            self.show_score_one(player_id)
                    else:
                        self.tft.fill(self.COLOR_BG)
                        self.tft.text(font, "Type number", 10, 20, st7789.color565(255,255,255), self.COLOR_BG)
                        self.tft.text(font, "new player", 10, 60, st7789.color565(255,255,255), self.COLOR_BG)
                        self.tft.text(font, "1-8:", 10, 100, st7789.color565(255,255,255), self.COLOR_BG)
                        self.state_game = "setRfid"
                        self.save_rfid = rfid_card
    
    def show_score_all(self):
        self.tft.fill(self.COLOR_BG)
        for i in range(0, 8):
            self.tft.text(font, f"{i+1}: {self.players[i]}", 10, i*40, st7789.color565(255,255,255), self.COLOR_BG)
    
    def show_score_one(self, player):
        self.tft.fill(self.COLOR_BG)
        for i in range(0, 8):
            if player == i:
                self.tft.text(font, f"{i+1}: {self.players[i]}", 10, i*40, st7789.color565(0,255,255), self.COLOR_BG)
            else:
                self.tft.text(font, f"{i+1}: {self.players[i]}", 10, i*40, st7789.color565(255,255,255), self.COLOR_BG)
        
    def show_score_one_number(self, number):
        self.tft.fill(self.COLOR_BG)
        if number > 99999:
            self.tft.text(font, str(number), 10, 20, st7789.color565(255,255,255), self.COLOR_BG)
        else:    
            self.tft.text(font, str(number), 10, 20, st7789.color565(255,255,255), self.COLOR_BG)
    
    def show_trade(self, number):
        self.tft.fill(self.COLOR_BG)
        self.tft.text(font, f"T{number}", 10, 20, st7789.color565(255,255,255), self.COLOR_BG)
    
    def show_plus(self, number):
        self.tft.fill(self.COLOR_BG)
        self.tft.text(font, f"+{number}", 10, 20, st7789.color565(255,255,255), self.COLOR_BG)
    
    def show_minus(self, number):
        self.tft.fill(self.COLOR_BG)
        self.tft.text(font, f"-{number}", 10, 20, st7789.color565(255,255,255), self.COLOR_BG)
    
    def show_not_enough(self, number):
        self.tft.fill(self.COLOR_BG)
        if int(self.number[:-1]) > 9999:
            self.tft.text(font, f"NO {number}", 10, 20, st7789.color565(255,255,255), self.COLOR_BG)
        else:
            self.tft.text(font, f"NO {number}", 10, 20, st7789.color565(255,255,255), self.COLOR_BG)

game = Game()
game.run_game()
