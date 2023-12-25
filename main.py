import os
import socket
import serial
import serial.tools.list_ports
import datetime
import json
import logging

#Настройка логирования
logging.basicConfig(level=logging.INFO, filename="py_log.log", filemode="w",
                    format="[%(asctime)s] <%(levelname)s> %(message)s")

'''
#Чтение второй этикетки
def ReadZPL(filePath, valsinTable):
    listNames = list()
    if not(os.path.exists(filePath)):
        return listNames, valsinTable
    else:
        print("Такой шаблон есть")
        try:
            _TemplateFile = open(filePath, 'r', encoding='UTF-8')
            strArray = _TemplateFile.read().split('^')
            print(strArray)
            index = 0
            while True:
                if (index >= len(strArray)):
                    break
                q = len(strArray[index]) > 3
                print(strArray[index][:2])
                if (q and strArray[index][:2] == "FN"):
                    if (len(strArray[index].split('"')) > 2):
                        listNames.append(strArray[index].split('"')[1])
                        valsinTable.append(strArray[index + 1][2:])
                        print(listNames)
                        print(valsinTable)
                        print("-----------")
                index += 1
        except Exception as e:
            print(f"Ошибка при чтении шаблона: {e}")
            logging.error(f"Ошибка при чтении шаблона: {e}")
    return listNames, valsinTable
'''
#Заполнение данных Шаблона этикетки
'''
dict:   time
        day
        weight
        shtuk
'''
def CompletionZPL(dict):
    _answerString = ""
    if os.path.exists("Template22_8.zpl"):
        _templateFile = open("Template22_8.zpl", 'r')
        _templateText = _templateFile.read()
        _stringArr = _templateText.split('^')
        count = 0
        tempString = ""
        _answerString += _stringArr[0]
        for i in range(1, len(_stringArr)):
            if _stringArr[i][:2] == "FN":
                match count:
                    case 0:
                        if (dict["day"]):
                            tempString = "FD" + dict["day"]
                        else:
                            tempString = "FD" + datetime.datetime.now().strftime("%d.%m.%y")
                    case 1:
                        if (dict["time"]):
                            tempString = "FD" + dict["time"]
                        else:
                            tempString = "FD" + datetime.datetime.now().strftime("%H:%M")
                    case 2:
                        tempString = "FD" + str(dict["weight"]) + dict["shtuk"]
                _stringArr[i] = tempString
                count += 1
                print(f"tempString:{tempString}")
            _answerString += '^' + _stringArr[i]
    return _answerString

#Отправка задания на Принтер
def SendToZebra(dataToSending, printer):
    _address = list(map(str, printer.split(':')))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((_address[0], int(_address[1])))
            strAns = CompletionZPL({"time":None, "day":None, "weight":dataToSending[1], "shtuk":dataToSending[2]})
            '''
            #_TemplateFile = open("Template22_8.zpl", 'r')
            _TemplateFile = open("Template50_100.zpl", 'r')
            _TemplateText = _TemplateFile.read()
            _bin_str = str.encode(_TemplateText, encoding='UTF-8')
            '''
            _bin_str = str.encode(strAns, encoding='UTF-8')
            print(_bin_str)
            client.sendall(_bin_str)
            print(f"Заглушка Отправка на Зебру {dataToSending}")
            logging.info(f"Заглушка Отправка на Зебру {dataToSending}")
    except Exception as e:
        print(f"Error Sending: {e}")
        logging.error(f"Error Sending: {e}")
    finally:
        client.close()


#Постоянная прослушка COM-порта
def AddListening(COMPort, printerPort):
    try:
        logging.info(f"Успешное добавление прослушивания для {COMPort.port} на Принтер {printerPort}")
        serialString = ""  # Used to hold data coming over UART
        while 1:
            # Wait until there is data waiting in the serial buffer
            if COMPort.in_waiting > 0:
                # Read data out of the buffer until a carraige return / new line is found
                serialString = COMPort.readline()
                # Print the contents of the serial data
                try:
                    s = serialString.decode("Ascii").split()
                    logging.info(f"{COMPort.port} получил: {s}")
                    print(s)
                    SendToZebra(s, printerPort)
                except:
                    print("ASDASASSD")
                    pass
    except:
        print("Тут ошибка при закрытии сервака!!!!!")
    finally:
        if _port.is_open:
            print("Порт был открыт")
            _port.close()

logging.info("Начало работы программы")
#Список всех доступных COM-портов
ports = serial.tools.list_ports.comports()
for port in ports:
    logging.info(f"{port}")
#Открытие конфигурации COM-портов
with open("config.json", 'r') as file:
    _config_params = json.load(file)
'''
print("------------------------------------------------------------------------------")
print(CompletionZPL({"time":"23:15", "day":"30.11.1999", "weight":1700, "shtuk":"kg"}))
print("------------------------------------------------------------------------------")
print(CompletionZPL({"time":"14:15", "day":None, "weight":1700, "shtuk":"kg"}))
print("------------------------------------------------------------------------------")
print(CompletionZPL({"time":None, "day":"30.11.1999", "weight":1700, "shtuk":"kg"}))
print("------------------------------------------------------------------------------")
print(CompletionZPL({"time":None, "day":None, "weight":1700, "shtuk":"kg"}))
'''
#Добавление в список всех доступных портов
COMPorts = list()
for weight in _config_params["weights"]:
    try:
        serialPort = serial.Serial(
            port=weight["COM"], baudrate=weight["baudrate"], bytesize=weight["bytesize"], timeout=weight["timeout"], stopbits=serial.STOPBITS_ONE
        )
        COMPorts.append(serialPort)
        logging.info(f"Успешное подключение к {weight['COM']}")
    except ValueError as ve:
        logging.error(f"COM-порт не найден: {ve}")
    except serial.SerialException as se:
        logging.error(f"COM-порт используется или недоступен: {se}")
    except Exception as e:
        logging.error(f"ERROR: {e}")
print(COMPorts)
for _port in COMPorts:
    AddListening(_port, "192.168.0.83:9100")

logging.info("Конец работы программы")