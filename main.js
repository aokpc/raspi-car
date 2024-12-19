import ipConfig from "./config.js"

// 画像格納変数
const img = {
    sample: [await Deno.readFile("./sample.png")],
    port: {},
    cache: {}
}

// TCPとWSを格納する変数
const ctl = {
    tcp: {
        sample: {
            write: (i) => {
                console.log(new TextDecoder().decode(i))
            }
        }
    },
    ws: {}
}
 
// UDPを読み取る
class UDPIsocket {
    constructor(dev) {
        this.conn = Deno.listenDatagram({ transport: "udp", port: 0, hostname: "0.0.0.0" });
        this.dev = dev
        img.cache[dev] = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], now: 0 }
    }
    async receive() {
        const recv = await this.conn.receive()
        const recvbuf = recv[0]
        //順番整理
        if (img.cache[this.dev].now > recvbuf[0] % 8) {
            if (recvbuf[0] % 8 !== 0) {
                return
            }
        }
        img.cache[this.dev].now = recvbuf[0] % 8
        //分割したデータを保存
        img.cache[this.dev][recvbuf[0] % 8][Math.floor(Math.floor(recvbuf[0] / 8) / 2)] = recvbuf.slice(1)

        //奇数は一番最後のデータ
        if (Math.floor(recvbuf[0] / 8) % 2 === 1) {

            let res = []

            setTimeout(() => {
                for (const e of img.cache[this.dev][recvbuf[0] % 8]) {
                    if (!e) {
                        return
                    }
                    res = [...res, ...e]
                }
                img.cache[this.dev][recvbuf[0] % 8] = []
                img[this.dev] = new Uint8Array(res)
            }, 20
            )
        }
        return
    }
}

function sleep(n) {
    return new Promise((resolve, ) => {
        setTimeout(() => {
            resolve()
        }, n);
    })
}

// TCPを受信
async function readTCP(dev) {
    const connection = ctl.tcp[dev]
    while (true) {
        const connectionWS = ctl.ws[dev]
        const buffer = new Uint8Array(64);
        await connection.read(buffer);
        try {
            connectionWS.send(new TextDecoder().decode(buffer).replace("\u0000", ""))
        } catch {
            continue
        }
    }
}
// UDPを作成 受信
function readUDP(d) {
    const s = new UDPIsocket(d)
    setTimeout(async () => {
        while (true) {
            await s.receive()
        }
    }, 100);
    return s
}

// _ TCPを作成
function initTCP(devs = []) {
    devs.forEach(async (dev) => {
        const ip = ipConfig[dev]
        const connection = await Deno.connect({
            port: 771,
            hostname: ip,
        });
        ctl.tcp[dev] = connection
        readTCP(dev)
        const udp = readUDP(dev)
        img.port[dev] = udp.conn.addr.port
    }
    )
}

// 画像用WSを受信した時に実行
function imgSock(req) {
    const url = new URL(req.url)
    const { response, socket } = Deno.upgradeWebSocket(req);
    const devId = url.searchParams.get("device")
    // 使用するポートを送信
    ctl.tcp[devId].write(new TextEncoder().encode("||img" + img.port[devId]))
    socket.onmessage = () => {
        socket.send(img[devId])
    }
    socket.onclose = () => {
        ctl.tcp[devId].write(new TextEncoder().encode("img0"))
    }
    return response
}

// GPIO用WSを受信した時に実行
function ctlSock(req) {
    const url = new URL(req.url)
    const { response, socket } = Deno.upgradeWebSocket(req);
    const devId = url.searchParams.get("device")
    socket.onmessage = (event) => {
        ctl.tcp[devId].write(new TextEncoder().encode("||" + event.data))
    }
    ctl.ws[devId] = socket
    return response
}

// HTTPリクエストを処理
async function handler(req) {
    const html = await Deno.readTextFile("./index.html")
    const url = new URL(req.url)
    console.log(req.url)
    switch (url.pathname) {
        case "/":
            return html.replaceAll("!devId", "sample")
        case "/01":
            return html.replaceAll("!devId", "01")
        case "/02":
            return html.replaceAll("!devId", "02")
        case "/03":
            return html.replaceAll("!devId", "03")
        case "/04":
            return html.replaceAll("!devId", "04")
        case "/05":
            return html.replaceAll("!devId", "05")
        case "/06":
            return html.replaceAll("!devId", "06")
        case "/0f":
            return html.replaceAll("!devId", "0f")
        case "/img":
            return imgSock(req)
        case "/control":
            return ctlSock(req)
        default:
            return "Err 404 :("
    }
}

// HTTPリクエストをいい感じに処理
async function respMaker(...args) {
    let res = await handler(...args)
    if (res.constructor == Response) {
        return res
    } else {
        res = res.toString()
        res = new Response(res, { headers: { "content-type": "text/html" }, status: 200 })
        return res
    }
}

// テスト用
async function sample() {
    const device = "01"
    // tcp作成
    const connection = await Deno.connect({
        port: 771,
        hostname: ipConfig[device],
    });
    ctl.tcp[device] = connection
    // tcp受信
    readTCP(device)

    // udp作成
    const udp = readUDP(device)
    img.port[device] = udp.conn.addr.port
}

await sample()

Deno.serve(respMaker)