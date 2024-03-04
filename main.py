import os
import socket
import serial.tools.list_ports
import datetime
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

#region Модели весов
#Возвращает словарь моделей весов
def GetModels():
    try:
        with open("ListModel.json", 'r') as file:
            _ListModels = json.load(file)
    except:
        _ListModels = dict()
        with open("ListModel.json", 'w') as file:
            json.dump(_ListModels, file, indent=4)
    return _ListModels

#Удаление модели весов
def DeleteModel(nameModel):
    models = GetModels()
    if models.get(nameModel, None):
        key_list = list(COMPorts.keys())
        listInterface = GetInterface()
        # Закрытие COM-портов, которые используют модель, которую нужно удалить
        for key in key_list:
            if listInterface[key]['model'] == nameModel:
                DeleteCOMPort(key)
        del models[nameModel]
        with open("ListModel.json", 'w') as file:
            json.dump(models, file, indent=4)
        print(f"Успешное удаление модели: {nameModel}")
        logging.info(f'Успешное удаление модели: {nameModel}')
    else:
        print("Такого значения в списке моделей нет")
        logging.error('Такого значения в списке моделей нет')
        return False
    return True

#Добавление/Изменение модели
def AddModel(dictModel):
    models = GetModels()
    models.update(dictModel)
    with open("ListModel.json", 'w') as file:
        json.dump(models, file, indent=4)
    listInterface = GetInterface()
    q = True
    l = list(COMPorts.keys())
    for key in l:
        if listInterface[key]['model'] == list(dictModel.keys())[0]:
            DeleteCOMPort(key)
            if not CreateNewCOMPort(dict.fromkeys([key], listInterface[key])):
                q = False
    if q:
        print(f"Успешное добавление/изменение модели: {dictModel}")
        logging.info(f'Успешное добавление/изменение модели: {dictModel}')
    else:
        print('Добавление интерфйса прошло. СОМ-порт не удалось перезапустить')
        logging.error('Добавление интерфйса прошло. СОМ-порт не удалось перезапустить')
    return q
#endregion

#region Интерфейс
#Возвращает словарь интерфейсов
def GetInterface():
    try:
        with open("ListInterface.json", 'r') as file:
            _ListInterface = json.load(file)
    except:
        _ListInterface = dict()
        with open("ListInterface.json", 'w') as file:
            json.dump(_ListInterface, file, indent=4)
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
    with open("ListInterface.json", 'w') as file:
        json.dump(ListInterface, file, indent=4)
    if CreateNewCOMPort(dictInterface):
        print(answer)
        logging.info(answer)
        return True
    else:
        print(f'COM-порт не запущен: {dictInterface}')
        logging.info(f'COM-порт не запущен: {dictInterface}')
        logging.info(answer)
        return False

#Удаление строки интерфейса
def DeleteInterface(numberWeight):
    ListInterface = GetInterface()
    if ListInterface.get(numberWeight, None):
        DeleteCOMPort(numberWeight)
        del ListInterface[numberWeight]
        ListInterface = dict(sorted(ListInterface.items()))
        with open("ListInterface.json", 'w') as file:
            json.dump(ListInterface, file, indent=4)
        print(f"Успешное удаление интерфейса: {numberWeight}")
        logging.info(f'Успешное удаление интерфейса: {numberWeight}')
    else:
        print("Такого значения в списке интерфейсов нет")
        logging.error('Такого значения в списке интерфейсов нет')
        return False
    return True
#endregion

#region COM-порт
#Возвращает список подключенных COM-портов
def GetCOMPorts():
    d = dict()
    for key in COMPorts:
        d[key]=None
    return d

#Закрывает все открытые COM-порта
def CloseAllCOMPorts():
    ports = COMPorts.copy()
    for interface in ports:
        DeleteCOMPort(interface)
    ports.clear()

#Открывает все COM-порта с файла интерфейса
def OpenALLCOMPorts():
    dictInterface = GetInterface()
    for key in dictInterface:
        interface = dict.fromkeys([key], dictInterface[key])
        CreateNewCOMPort(interface)

#Перезапуск всех доступных COM-портов
def ReloadCOMPorts():
    CloseAllCOMPorts()
    OpenALLCOMPorts()

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
                    port=dictCOM[key]["weightIP/COM"],
                    baudrate=model["baudrate"],
                    bytesize=model["bytesize"],
                    timeout=model["timeout"],
                    stopbits=serial.STOPBITS_ONE
                )
                if dictCOM[key]["model"] == "CKE-60-4050":
                    thread = threading.Thread(target=AddAlwaysListening, args=(key, dictCOM[key]["printerIP"]))
                else:
                    thread = threading.Thread(target=AddListening, args=(key, dictCOM[key]["printerIP"]))
                COMPort = {key: (serialPort, thread)}
                COMPorts.update(COMPort)
                thread.start()
                print(f"Успешное подключение к {dictCOM[key]['weightIP/COM']}")
                logging.info(f"Успешное подключение к {dictCOM[key]['weightIP/COM']}")
                return True
            except ValueError as ve:
                logging.error(f"COM-порт не найден: {ve}")
                return False
            except serial.SerialException as se:
                logging.error(f"COM-порт используется или недоступен: {se}")
                return False
            except Exception as e:
                logging.error(f"Ошибка при создании COM-порта: {e}")
                return False
        else:
            #print(f"Создание сокета на {dictCOM[key]['weightIP/COM']}")
            return False
    else:
        print(f"Не могу создать {dictCOM[key]['weightIP/COM']}-порт с такой моделью(Возможно отсутствует данные этой модели)")
        logging.error(f"Не могу создать {dictCOM[key]['weightIP/COM']}-порт с такой моделью(Возможно отсутствует данные этой модели)")
        return False

#Перевод данных с COMорта в массив данных для шаблона
def DataToWeight(strCOM):
    s = ""
    v = ""
    num = False
    for c in strCOM:
        if c.isdigit() or c == '.' or c == ',':
            num = True
            s += c
        elif num and c != ' ':
            v += c
    return [s, v]

#Прослушка COMпорта
def AddAlwaysListening(key, printerPort):
    COMPort = COMPorts[key][0]
    try:
        logging.info(f"Успешное добавление прослушивания для {COMPort.port} на Принтер {printerPort}")
        prev = 0.0
        count = 0
        while 1:
            if COMPort.in_waiting > 0:
                # Read data out of the buffer until a carraige return / new line is found
                serialString = COMPort.readline()
                # Print the contents of the serial data
                try:
                    weight = DataToWeight(serialString.decode("Ascii"))
                    if weight[0] != '':
                        s = float(weight[0])
                        if s < prev + 0.3 and s > prev - 0.3 and (s > 0.1):
                            if count < 30:
                                count += 1
                            elif count == 30:
                                logging.info(f"{COMPort.port} получил: {weight}")
                                count += 1
                                thread = threading.Thread(target=SendToZebra, args=(weight, key))
                                thread.start()
                        else:
                            count = 0
                        prev = s
                except:
                    pass
    except:
        print(f"Прерывание прослушивания {COMPort.port}!")
        logging.info(f'Прерывание прослушивания {COMPort.port}!')
    finally:
        if COMPort.is_open:
            COMPort.close()

#Постоянная прослушка COM-порта
def AddListening(key, printerPort):
    COMPort = COMPorts[key][0]
    try:
        logging.info(f"Успешное добавление прослушивания для {COMPort.port} на Принтер {printerPort}")
        serialString = ""  # Used to hold data coming over UART
        while 1:
            #print(COMPort.readline())
            # Wait until there is data waiting in the serial buffer
            if COMPort.in_waiting > 0:
                # Read data out of the buffer until a carraige return / new line is found
                serialString = COMPort.readline()
                # Print the contents of the serial data
                try:
                    weight = DataToWeight(serialString.decode("Ascii"))
                    if weight[0] != '':
                        logging.info(f"{COMPort.port} получил: {weight}")
                        thread = threading.Thread(target=SendToZebra, args=(weight, key))
                        thread.start()
                except:
                    pass
    except:
        print(f"Прерывание прослушивания {COMPort.port}!")
        logging.info(f'Прерывание прослушивания {COMPort.port}!')
    finally:
        if COMPort.is_open:
            COMPort.close()

#region Zebra
#Создание этикетки с данными
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
                        if (dict["data"]):
                            tempString = "FD" + dict["data"]
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
            _answerString += '^' + _stringArr[i]
    else:
        print('Отсутствует файл шаблона этикетки')
        logging.error('Отсутствует файл шаблона этикетки')
    return _answerString

def CreateTemplateDict(dataToSending, key):
    d = dict()
    listInterface = GetInterface()
    if listInterface[key]['time'] == "":
        d['time'] = None
    else:
        d['time'] = listInterface[key]['time']
    if listInterface[key]['data'] == "":
        d['data'] = None
    else:
        d['data'] = listInterface[key]['data']
    d['weight'] = dataToSending[0]
    d['shtuk'] = dataToSending[1]
    return d

#Отправка задания на Принтер
def SendToZebra(dataToSending, key):
    printer = GetInterface()[key]['printerIP']
    _address = list(map(str, printer.split(':')))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((_address[0], int(_address[1])))
            strAns = CompletionZPL(CreateTemplateDict(dataToSending, key))
            _bin_str = str.encode(strAns, encoding='UTF-8')
            client.sendall(_bin_str)
            print(f"Отправка на Зебру: {dataToSending}")
            logging.info(f"Отправка на Зебру: {dataToSending}")
    except Exception as e:
        print(f"Ошибка при отправке данных на Зебру: {e}")
        logging.error(f"Ошибка при отправке данных на Зебру: {e}")
    finally:
        client.close()
#endregion

#endregion

#Мини-сервер API
def CreateServer(host, port):
    class HandleRequests(BaseHTTPRequestHandler):
        logging.info(f'Успешный запуск сервера API по адресу: {host}:{port}')
        def _set_headers(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

        def do_GET(self):
            self._set_headers()
            ans = ''
            logging.info(f'Получен запрос GET: {self.path}')
            if self.path == '/Models':
                ans = str(GetModels())
            elif self.path == '/Interfaces':
                ans = str(GetInterface()) + ';' + str(GetCOMPorts())
            ans = ans.encode('utf-8')
            self.wfile.write(ans)

        def do_POST(self):
            logging.info(f'Получен запрос POST: {self.path}')
            if self.path == '/AddInterface' or self.path == '/ChangeInterface':
                ans = ''
                try:
                    l = self.headers['Content-Length']
                    text = self.rfile.read(int(l)).decode()
                    d = eval(text)
                    if not AddInterface(d):
                        ans = 'Not Added'
                        self.send_response(200)
                    else:
                        ans = 'Added'
                        self.send_response(201)
                except Exception as e:
                    print(f'Ошибка при обработке POST-запроса: {e}')
                    logging.error(f'Ошибка при обработке POST-запроса: {e}')
                    ans = 'Error'
                    self.send_response(400)
                #self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(ans.encode('utf-8'))
            if self.path == '/AddModel' or self.path == '/ChangeModel':
                ans = ''
                try:
                    l = self.headers['Content-Length']
                    text = self.rfile.read(int(l)).decode('utf-8')
                    d = eval(text)
                    key = list(d.keys())[0]
                    d[key]['baudrate'] = int(d[key]['baudrate'])
                    d[key]['bytesize'] = int(d[key]['bytesize'])
                    d[key]['timeout'] = int(d[key]['timeout'])
                    if AddModel(d):
                        ans = 'Added'
                        self.send_response(201)
                    else:
                        ans = 'Not Added'
                        self.send_response(200)
                except Exception as e:
                    print(f'Ошибка при обработке POST-запроса: {e}')
                    logging.error(f'Ошибка при обработке POST-запроса: {e}')
                    ans = 'Error'
                    self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(ans.encode('utf-8'))

        def do_PUT(self):
            logging.info(f'Получен запрос PUT: {self.path}')
            if self.path == '/ReloadInterfaces':
                self._set_headers()
                try:
                    ReloadCOMPorts()
                    ans = 'Reloaded'
                except Exception as e:
                    ans = 'Not reloaded'
                    print(f'Ошибка при обработке PUT-запроса: {e}')
                    logging.error(f'Ошибка при обработке PUT-запроса: {e}')
                self.wfile.write(ans.encode('utf-8'))
            if self.path == '/ChangeInterface' or self.path == '/ChangeModel':
                self.do_POST()

        def do_DELETE(self):
            logging.info(f'Получен запрос DELETE: {self.path}')
            ans = dict()
            if self.path == '/Interfaces':
                try:
                    l = self.headers['Content-Length']
                    text = self.rfile.read(int(l)).decode()
                    d = eval(text)
                    for key in d:
                        if not DeleteInterface(key):
                            ans[key] = False
                    self.send_response(201)
                except Exception as e:
                    self.send_response(400)
                    print(f'Ошибка при обработке DELETE-запроса: {e}')
                    logging.error(f'Ошибка при обработке DELETE-запроса: {e}')
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                ans = str(ans)
                self.wfile.write(ans.encode('utf-8'))
            if self.path == '/Models':
                ans = dict()
                try:
                    l = self.headers['Content-Length']
                    text = self.rfile.read(int(l)).decode()
                    d = eval(text)
                    for model in d:
                        if DeleteModel(model):
                            ans[model] = True
                    self.send_response(201)
                except Exception as e:
                    self.send_response(400)
                    print(f'Ошибка при обработке DELETE-запроса: {e}')
                    logging.error(f'Ошибка при обработке DELETE-запроса: {e}')
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                ans = str(ans)
                self.wfile.write(ans.encode('utf-8'))
    try:
        httpd = HTTPServer((host, int(port)), HandleRequests).serve_forever()
    except Exception:
        logging.error('Прекращение работы сервера API')

if __name__ == '__main__':
    #Загрузка параметров работы программы
    try:
        with open("config.json", 'r') as file:
            _config_params = json.load(file)
    except:
        with open("config.json", 'w') as file:
            _config_params = dict()
            _config_params['server'] = {'port' : '8080'}
            _config_params['Log'] = {'Log_path' : "py_log.log", "Filemod" : "w"}
            json.dump(_config_params, file, indent=4)

    #Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        filename=_config_params['Log']['Log_path'],
        filemode=_config_params['Log']['Filemod'],
        format="[%(asctime)s] <%(levelname)s> %(message)s")
    logging.info("Начало работы программы")
    #Список всех доступных COM-портов
    ports = serial.tools.list_ports.comports()
    for port in ports:
        logging.info(f"{port}")
    # Поле собственного IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    server_ip = s.getsockname()[0]
    s.close()
    thread = threading.Thread(target=CreateServer, args=(server_ip, _config_params['server']['port']))
    thread.start()
    COMPorts = dict()
    OpenALLCOMPorts()
    print("Конец добавления портов")
    for com in COMPorts:
        print(f'{com} : {COMPorts[com]}')