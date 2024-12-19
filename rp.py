import socket,json,threading,cv2,time,pigpio,subprocess
# pigpioデーモン起動 
subprocess.call(["pigpiod"])

# tcp
# ホスト:LAN内 (0.0.0.0)
# ポート:771
ADDR = ("0.0.0.0", 771)

# tcpのソケット作成
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# ADDRにバインド (host,portを設定)
server.bind(ADDR)

# 接続を待つのを開始
server.listen()

# 画像送信の変数、thread内のwhile文を抜けるために使う
imgStart:int = 0

# サーバーのIPを代入する変数
serverIP:str = None

# pigpioを初期化、ピン設定
pi = pigpio.pi()
# サーボ用PWM
pi.set_mode(12, pigpio.OUTPUT)
# レーザー
pi.set_mode(5, pigpio.OUTPUT)
# モーター左
pi.set_mode(6, pigpio.OUTPUT)
# モーター左
pi.set_mode(13, pigpio.OUTPUT)
# モーター右
pi.set_mode(19, pigpio.OUTPUT)
# モーター右
pi.set_mode(26, pigpio.OUTPUT)

print("""
---------------GPIO---------------
 1 2  [       |3V3] [       |5V ]
 3 4  [       |2  ] [       |5V ]
 5 6  [       |3  ] [       |GND]
 7 8  [       |4  ] [       |14 ]
 9 10 [       |GND] [       |15 ]
11 12 [       |17 ] [       |18 ]
13 14 [       |27 ] [       |GND]
15 16 [       |22 ] [       |23 ]
17 18 [       |3V3] [       |24 ]
19 20 [       |10 ] [       |GND]
21 22 [       |9  ] [       |25 ]
23 24 [       |11 ] [       |8  ]
25 26 [       |GND] [       |7  ]
27 28 [       |0  ] [       |1  ]
29 30 [ razer |5  ] [       |GND]
31 32 [motor L|6  ] [ servo |12 ]
33 34 [motor L|13 ] [       |GND]
35 36 [motor R|19 ] [       |16 ]
37 38 [motor R|26 ] [       |20 ]
39 40 [       |GND] [       |21 ]
----------------------------------
""")

# コントロール状態
status:dict = {}

# gpio制御
def setgpio(data:dict):
    global status
    status = data
    print(f"{data['m']['l'].zfill(2)}L({(data['c']or"").zfill(5)}/{data['r']}){data['m']['r'].zfill(2)}R")
    
    # モーターL逆転
    if data['m']['l'] == -1:
        pi.write(6, 1)
        pi.write(13, 0)
    # モーターL正転
    elif data['m']['l'] == 1:
        pi.write(6, 0)
        pi.write(13, 1)
    # モーターL停止 
    elif data['m']['l'] == 0:
        pi.write(6, 0)
        pi.write(13, 0)
    
    # モーターR逆転
    if data['m']['r'] == -1:
        pi.write(26, 1)
        pi.write(19, 0)
    # モーターR正転
    elif data['m']['r'] == 1:
        pi.write(26, 0)
        pi.write(19, 1)
    # モーターR停止
    elif data['m']['l'] == 0:
        pi.write(19, 0)
        pi.write(26, 0)
    
    # レーザーoff
    if data['r'] == 0:
        pi.write(5, 0)
    # レーザーon
    elif data['r'] == 1:
        pi.write(5, 1)

# サーボ回転
def rorateCamera():
    global status
    r=90
    while True:
        time.sleep(0.1)
        if status.get("c") is None:
            continue
        # c(カメラ)がresetの時90度
        if status.get("c")=="reset":
            r=90
        
        # c_d(カメラ移動)が存在する時角度変化
        if status.get("c_d"):
            r+=(status.get("c_d"))
        # max
        if r>175:
            r=175
        # min
        if r<5:
            r=5
        # PWM
        pi.hardware_PWM(12,50,25000+int(95000*(r/180)))

# 画像サイズ調節
def scale_to_height(img, height):
        try:
            h, w = img.shape[:2]
            width = round(w * (height / h))
            dst = cv2.resize(img, dsize=(width, height))
            return dst
        except:
            pass

# カメラ画像送信
def imgSender(ip,port):
    global imgStart
    # imgStartを+1 ,他のスレッド内の imgStart==check がfalseして終了する
    check = imgStart+1
    imgStart = check
    
    #　udp作成
    ADDR = (ip, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # index:0 のカメラを取得
    cap = cv2.VideoCapture(0)
    
    # fps:30
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # udp検証用int
    j = 0
    
    # ループ imgStartが変化すると終了
    while imgStart==check:
        try:
            # カメラ画像取得
            _,_img = cap.read()
            # 画像縮小
            img = scale_to_height(_img,180)
            # 表示がおかしい場合,画像回転
            #img=cv2.flip(img,-1)
            # jpegにする
            _, ndarray = cv2.imencode('.jpeg', img)
            # byteにする
            bts = ndarray.tobytes()
            # パケット分割用カウンター
            i = 0
            # 画像データをパケットに分割して送信 8000byteごと
            while len(bts)>8000:
                # 8000byte分切り取る
                sbts = bts[0:8000]
                bts = bts[8000:]
                # 送信 1バイト目が識別用 2バイト目からがデータ
                sock.sendto(chr((i*2)*8+j).encode() + sbts, ADDR)
                # カウンター +1
                i += 1
            sock.sendto(chr((i*2+1)*8+j).encode()+bts, ADDR)
            
            # ループ遅延
            time.sleep(0.1)
            
            j += 1
            if j == 8:
                j = 0
        except:
            pass
    cap.release()

# gpio処理用 コントローラーに返すものがあるならここ'client.send'に書く
def gpioControl(client,gpio):
    setgpio(gpio)
    client.send(b'{}')

# カメラ回転開始
threading.Thread(target=rorateCamera).start()

while True:
        # tcpが接続されるまで待つ
        client, addr = server.accept()
        print(addr)
        serverIP,_ = addr
        client.send(b"{}")
        
        while True:
            # データ受信
            data = client.recv(4096)
            # 切断でない時?
            if data != b"":
                data = data.decode()
                # データ処理, ||で区切られている
                for splitdata in data.split("||"):
                    # 画像送信要求(img+ポート)
                    if splitdata[0:3] == "img":
                        port = int(splitdata[3:])
                        # 停止
                        if port == 0:
                            imgStart = 0
                            continue
                        # 画像送信スレッド
                        threading.Thread(target = imgSender,args = (serverIP,port)).start()
                        continue
                    try:
                        # json変換, 処理
                        gpioControl(client,(json.loads(splitdata)))
                    except:
                        continue
                    # 切断
                    if data == b"exit.":
                        print("break")
                        client.close()
                    break
            else:
                # 切断
                client.close()
                break
        imgStart = 0