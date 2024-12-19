# 起動方法

コンソールを２個開く

コンソール1
```sh
# wifi kpcnavyに接続
ssh kpc@0fd.local # password 771771
# raspi
sudo pigpiod
sudo python serve.py
```

コンソール2
```sh
# wifi kpcnavyに接続
cd 解凍フォルダのパス
ping 0fd.local # ipをコピー
# config.js の"01":"~"にipを貼り付ける
deno run --unstable --allow-all ./main.js
```

ブラウザで [ラジコン](http://127.0.0.1:8000/01) を開く

カメラが映らなかったりしたら`ctl+c`で終了して`sudo python serve.py`->`deno run --unstable --allow-all ./main.js`の順で実行し直す