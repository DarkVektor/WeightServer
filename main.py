import os
import socket
import serial.tools.list_ports
import datetime
import json
import logging
import threading

#Настройка логирования
logging.basicConfig(level=logging.INFO, filename="py_log.log",filemode="w",
                    format="[%(asctime)s] <%(levelname)s> %(message)s")

#region Модели весов
#Возвращает словарь моделей весов
def GetModels():
    with open("ListModel.json", 'r') as file:
        _ListModels = json.load(file)
    return _ListModels

#Удаление модели весов
def DeleteModel(nameModel):
    answer = list()
    models = GetModels()
    if models.get(nameModel, None):
        key_list = COMPorts.keys()
        listInterface = GetInterface()
        # Закрытие COM-портов, которые используют модель, которую нужно удалить
        for key in key_list:
            if listInterface[key]['model'] == nameModel:
                DeleteCOMPort(key)
                answer.append(key)
        del models[nameModel]
        with open("ListModel.json", 'w') as file:
            json.dump(models, file, indent=4)
        print("Успешное удаление")
    else:
        print("Такого значения в списке моделей нет")
    return answer

#Добавление/Изменение модели
def AddModel(dictModel):
    models = GetModels()
    models.update(dictModel)
    with open("ListModel.json", 'w') as file:
        json.dump(models, file, indent=4)
    print("Успешное добавление/изменение модели")
#endregion

#region Интерфейс
#Возвращает словарь интерфейсов
def GetInterface():
    with open("ListInterface.json", 'r') as file:
        _ListInterface = json.load(file)
    return _ListInterface

#Добавление нового Интерфейса / Перезапись интерфейса весов
def AddInterface(dictInterface):
    answer = "интерфейса весов"
    ListInterface = GetInterface()
    key = list(dictInterface.keys())[0]
    if ListInterface.get(key, None):
        #Если интерфейс есть, то нужно его обновить
        DeleteCOMPort(key)
        answer = "Успешное изменение " + answer
    else:
        answer = "Успешное добавление " + answer
    #Такого интерфейса ещё нет, нужно создать новый и подключить его
    ListInterface.update(dictInterface)
    CreateNewCOMPort(dictInterface)
    with open("ListInterface.json", 'w') as file:
        json.dump(ListInterface, file, indent=4)
    print(answer)

#Удаление строки интерфейса
def DeleteInterface(numberWeight):
    ListInterface = GetInterface()
    if ListInterface.get(numberWeight, None):
        DeleteCOMPort(numberWeight)
        del ListInterface[numberWeight]
        ListInterface = dict(sorted(ListInterface.items()))
        with open("ListInterface.json", 'w') as file:
            json.dump(ListInterface, file, indent=4)
        print("Успешное удаление")
    else:
        print("Такого значения в списке интерфейсов нет")
#endregion

#Возвращает список подключенных COM-портов
def GetCOMPorts():
    return COMPorts

def CloseAllCOMPorts():
    ports = COMPorts.copy()
    for interface in ports:
        DeleteCOMPort(interface)
    ports.clear()


#Закрытие открытого COM-порта(РАБОТАЕТ КОСТЫЛЬНО)
def DeleteCOMPort(numberWeight):
    if COMPorts.get(numberWeight, None):    #Проверка на существование этого порта
        COMPorts[numberWeight][0].close()
        del COMPorts[numberWeight]

#Открытие соединения на COM-порт
def CreateNewCOMPort(dictCOM):
    key = list(dictCOM.keys())[0]
    DeleteCOMPort(key)    #Удаляет соединение, если оно существовало
    model = GetModels().get(dictCOM[key]["model"], None)
    if model:   #Существует ли данные по текущей модели интерфейса
        if "COM" in dictCOM[key]["weightIP/COM"]:    #Если это COM-порт, то создается как COM-порт, иначе через сокет
            try:
                serialPort = serial.Serial(
                    port=dictCOM[key]["weightIP/COM"], baudrate=model["baudrate"], bytesize=model["bytesize"], timeout=model["timeout"],
                    stopbits=serial.STOPBITS_ONE
                )
                thread = threading.Thread(target=AddListening, args=(key, dictCOM[key]["printerIP"]))
                COMPort = {key: (serialPort, thread)}
                COMPorts.update(COMPort)
                thread.start()
                print(f"Успешное подключение к {dictCOM[key]['weightIP/COM']}")
                logging.info(f"Успешное подключение к {dictCOM[key]['weightIP/COM']}")
            except ValueError as ve:
                logging.error(f"COM-порт не найден: {ve}")
            except serial.SerialException as se:
                logging.error(f"COM-порт используется или недоступен: {se}")
            except Exception as e:
                logging.error(f"ERROR: {e}")
        else:
            print(f"Создание сокета на {dictCOM[key]['weightIP/COM']}")
    else:
        print("Не могу создать COM-порт с такой моделью(Возможно отсутствует данные этой модели)")
        logging.error("Не могу создать COM-порт с такой моделью(Возможно отсутствует данные этой модели)")

#Постоянная прослушка COM-порта
def AddListening(key, printerPort):
    COMPort = COMPorts[key][0]

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
                    #SendToZebra(s, key)
                except:
                    print("ASDASASSD")
                    pass
    except:
        print(f"Прерывание прослушивания {COMPort.port}!!!!!")
    finally:
        if COMPort.is_open:
            COMPort.close()


'''
def CreateCOMPorts(COMPortsL):
    for _port in COMPortsL:
        t = threading.Thread(target=AddListening, args=(_port, "192.168.0.83:9100"))
        t.start()
        ThreadingList.append(t)
'''
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

def CreateTemplateDict(dataToSending, key):
    d = dict()
    listInterface = GetInterface()
    if listInterface[key]['time'] == "":
        d['time'] = None
    else:
        d['time'] = listInterface[key]['time']
    if listInterface[key]['day'] == "":
        d['day'] = None
    else:
        d['day'] = listInterface[key]['day']
    d['weight'] = dataToSending[1]
    d['shtuk'] = dataToSending[2]
    return d

#Отправка задания на Принтер
def SendToZebra(dataToSending, key):
    printer = GetInterface()[key]['printerIP']
    _address = list(map(str, printer.split(':')))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((_address[0], int(_address[1])))
            strAns = CompletionZPL(CreateTemplateDict(dataToSending, key))
            #strAns = CompletionZPL({"time":None, "day":None, "weight":dataToSending[1], "shtuk":dataToSending[2]})
            '''
            #_TemplateFile = open("Template22_8.zpl", 'r')
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



logging.info("Начало работы программы")
#Список всех доступных COM-портов
ports = serial.tools.list_ports.comports()
for port in ports:
    logging.info(f"{port}")

#Открытие конфигурации COM-портов
with open("config.json", 'r') as file:
    _config_params = json.load(file)

COMPorts = dict()
ThreadingList = list()
dictInterface = GetInterface()
for key in dictInterface:
    interface = dict.fromkeys([key],dictInterface[key])
    CreateNewCOMPort(interface)
print("Конец добавления портов")
print(COMPorts)

AddInterface(
    {"3": {
    "weightIP/COM": "COM3",
    "model": "CAS HD 60",
    "printerIP": "192.168.0.83:9100",
    "data": "",
    "time": ""}
})
print(COMPorts)
AddInterface(
    {"3": {
    "weightIP/COM": "COM3",
    "model": "CAS HD 60",
    "printerIP": "192.168.0.84:9100",
    "data": "",
    "time": ""}
})
print(COMPorts)
#CloseAllCOMPorts()
print(COMPorts)

logging.info("Конец работы программы")
'''
for weight in _config_params["weights"]:
    try:
        serialPort = serial.Serial(
            port=weight["COM"], baudrate=weight["baudrate"], bytesize=weight["bytesize"], timeout=weight["timeout"],
            stopbits=serial.STOPBITS_ONE
        )
        COMPortsL.append(serialPort)
        logging.info(f"Успешное подключение к {weight['COM']}")
    except ValueError as ve:
        logging.error(f"COM-порт не найден: {ve}")
    except serial.SerialException as se:
        logging.error(f"COM-порт используется или недоступен: {se}")
    except Exception as e:
        logging.error(f"ERROR: {e}")
'''
#asyncio.get_event_loop().run_until_complete(CreateCOMPorts(COMPorts))
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


