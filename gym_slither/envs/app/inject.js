/**
 * This script uses various hacks to interact with the game. It is injected into the active browser
 * window and provides a simple HTTP API for playing the game and more specifically, for framing it
 * as an reinforcement learning task.
 */

var remote = require('electron').remote;
var express = remote.require("express");

remote.app.log("Starting game...");
document.getElementById('nick').value = '';
document.onkeydown({keyCode: 13});
window.onmousemove = null;

let clientX = 0;
let clientY = 0;
let hold = 0;

var engine = {
    quit: function () {
        remote.app.quit();
    },
    done: function () {
        var el = document.querySelector("#playh .nsi .nsi");
        var text = el.innerText.trim()
        return text === "Play Again";
    },
    ready: function () {
        var el = document.querySelector("#playh .nsi .nsi");
        el.innerText = "Play"
        document.onkeyup({'keyCode': 38});
        el = document.querySelector(".nsi span span");
        text = el.parentElement.children[1].innerText = "10"
        return document.querySelector("#login").style.display === "none"
    },
    get_score: function () {
        try {
            if(window.snake) {
                return 15 * (window.fpsls[window.snake.sct] + window.snake.fam /
                    window.fmlts[window.snake.sct] - 1) - 5;
            } else {
                 return 10;
            }
        } catch (e) {
            return 10;
        }
    },
    get_angle: function () {
        return window.snake.ang || 3.14
    },
    get_width: function() {
        return window.snake.sc
    },
    get_image: function (callback) {
        document.querySelector("body > div:nth-child(14)").style.display = "none"
        document.querySelector("body > div:nth-child(15)").style.display = "none"
        document.querySelector("body > div:nth-child(16)").style.display = "none"
        document.querySelector("body > div:nth-child(17)").style.display = "none"
        document.querySelector("body > div:nth-child(18)").style.display = "none"
        document.querySelector("body > div:nth-child(20)").style.display = "none"

        ang = window.snake.ang
        remote.app.screenshot().then(buffer => {
            callback(buffer, ang)
        })
        //
        // var el = document.querySelector("canvas.nsi");
        // // var data = el.toDataURL().replace(/^data:image\/\w+;base64,/, "");
        // // return new Buffer(data, 'base64')
        // el.toBlob((blob) => {
        //     blob.arrayBuffer().then((buf) => {
        //         callback(Buffer.from(buf))
        //     })
        // })
    },
    get_mouse: function () {
        w = window.innerWidth
        h = window.innerHeight
        return [clientX / w, clientY / h, hold, this.get_angle()]
    },
    move_mouse: function (x, y, hold) {
        window.xm = x
        window.ym = y
        if (hold)
            document.onkeydown({'keyCode': 38});
        else
            document.onkeyup({'keyCode': 38});
        w = window.innerWidth
        h = window.innerHeight
        el = document.getElementById("pointer")
        if (!el) {
            el = document.createElement('div');
            el.id = "pointer"
            el.style.position = "fixed"
            el.style.left = "0px"
            el.style.right = "0px"
            el.style.width = "2px"
            el.style.height = "2px"
            el.style.zIndex = "99999999"
            el.style.background = "#FFFFFF"
            document.body.appendChild(el)
            // document.body.innerHTML += '<div id="pointer" style="position:absolute;margin-left:-8px;margin-top:-8px;width:10px;height:10px;opacity:1;z-index:100;background:#FFFFFF;"></div>';
            // el = document.getElementById("pointer")
        }
        el.style.marginLeft = w / 2.0 + x
        el.style.marginTop = h / 2.0 + y
    },
    key_press: function (keyCode, duration, callback) {
        document.onkeydown({'keyCode': keyCode});
        setTimeout(function () {
            document.onkeyup({'keyCode': keyCode});
            if (callback) callback();
        }, duration)
    }
}

// setInterval(function () {
//     if (engine.done()) {
//         remote.app.log("Detected game over, exiting automatically....");
//         setTimeout(function () {
//             engine.quit();
//         }, 10000);
//     }
// }, 30000);

document.onmousemove = (event) => {
    clientX = event.clientX
    clientY = event.clientY
}

document.onmousedown = () => {
    hold = 1
}

document.onmouseup = () => {
    hold = 0
}

setTimeout(function () {
    if (!engine.ready()) {
        remote.app.log("Game didn't start in time, exiting...");
        engine.quit();
    } else {
        remote.app.log("Game running...");
    }
}, 30000)

remote.app.log("Starting server on port " + PORT_NUM + "...");
var server = express();
server.listen(PORT_NUM);

server.use(function (req, res, next) {
    remote.app.log("GET " + req.originalUrl);
    next()
});

server.get("/quit", function (req, res) {
    res.status(202).send();
    engine.quit()
})

server.get("/done", function (req, res) {
    res.status(202).send(String(engine.done()));
    //if (engine.done()) engine.quit();
});

server.get("/ready", function (req, res) {
    document.onkeydown({keyCode: 13});
    res.status(202).send(String(engine.ready()));
});

server.get("/state", function (req, res) {
    engine.get_image(function (img, ang) {
        res.writeHead(200, {
            'Content-Type': 'image/png',
            'Content-Length': img.length,
            'Snake-Angle': window.snake.ang
        });
        res.end(img);
    });
    // res.writeHead(200, {
    //     'Content-Type': 'image/png',
    //     'Content-Length': img.length
    // });
    // res.end(img);
})


server.get("/angle", function (req, res) {
    res.send(String(engine.get_angle()));
})

server.get("/snake-width", function (req, res) {
    res.send(String(engine.get_width()));
})

server.get("/score", function (req, res) {
    res.send(String(engine.get_score()));
})

server.get("/get-mouse", function (req, res) {
    res.send(String(engine.get_mouse()));
})

server.get("/mouse/:x/:y/:hold", function (req, res) {
    engine.move_mouse(parseFloat(req.params.x), parseFloat(req.params.y), parseInt(req.params.hold) === 1)
    res.end();
})

server.get("/action/:command/:duration", function (req, res) {
    var keyCode = false;
    if (req.params.command === "left") keyCode = 37;
    if (req.params.command === "right") keyCode = 39;
    if (req.params.command === "speed") keyCode = 32;
    engine.key_press(keyCode, parseInt(req.params.duration), function () {
        res.end();
    });
})

remote.app.log("Listening...");
