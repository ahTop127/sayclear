(function () {
  const SCENE = {
    c: {
      spoken: "把这个 button 改小一点，再把 padding 调一下，那个 hover 状态的颜色太暗了。",
      text: "1. 把 button 改小\n2. 调整 padding\n3. 把 hover 状态的颜色调亮",
    },
    b: {
      spoken: "这个页面有几个地方需要改，按钮太大了，颜色也需要调整一下，然后整体再简洁一点。",
      text: "1. 缩小按钮尺寸\n2. 调整页面颜色\n3. 简化整体页面设计",
    },
  };

  const STRIPES = 7;

  const body = document.body;
  const inputBox = document.getElementById("input-box");
  const composer = document.getElementById("composer");
  const sendNote = document.getElementById("send-note");
  const hud = document.getElementById("hud");
  const appAi = document.getElementById("app-ai");
  const appStack = document.getElementById("app-stack");
  const appReader = document.getElementById("app-reader");
  const sendBtn = document.getElementById("send-btn");
  const spokenNote = document.getElementById("spoken-note");

  let scene = "c";
  let screen = "flow";
  let filledText = SCENE.c.text;

  function sceneText() {
    return SCENE[scene].text;
  }

  function setPlaceholder(withCaret) {
    inputBox.innerHTML =
      '<span class="placeholder">问点什么…</span>' +
      (withCaret ? '<span class="caret"></span>' : "");
  }

  function setFilled(text, withCaret) {
    inputBox.textContent = text;
    if (withCaret) {
      inputBox.insertAdjacentHTML("beforeend", '<span class="caret"></span>');
    }
  }

  function showHud(html, extraClass) {
    hud.className = "hud is-on" + (extraClass ? " " + extraClass : "");
    hud.innerHTML = html;
  }

  function hideHud() {
    hud.className = "hud";
    hud.innerHTML = "";
  }

  function stripeHtml() {
    var html = "";
    var i;
    for (i = 0; i < STRIPES; i++) {
      html += "<i></i>";
    }
    return html;
  }

  function bindRecordBar() {
    var cancel = document.getElementById("rec-cancel");
    var ok = document.getElementById("rec-ok");
    if (cancel) {
      cancel.addEventListener("click", function () {
        go("idle");
      });
    }
    if (ok) {
      ok.addEventListener("click", function () {
        go("process");
      });
    }
  }

  function renderHud() {
    if (screen === "record") {
      showHud(
        '<div class="rec-bar" role="group" aria-label="正在录音">' +
          '<button type="button" class="rec-x" id="rec-cancel" aria-label="取消这次说话">×</button>' +
          '<div class="wave-stripes" aria-hidden="true">' +
          stripeHtml() +
          "</div>" +
          '<button type="button" class="rec-ok" id="rec-ok">OK</button>' +
          "</div>" +
          '<p class="rec-caption">正在录音 · 再按 <span class="kbd">⌘</span> 结束（单击切换，非按住）</p>',
        "rec"
      );
      bindRecordBar();
      return;
    }
    if (screen === "process") {
      showHud('<div class="think-pill">Thinking</div>', "think");
      return;
    }
    if (screen === "fail-mic") {
      showHud(
        '<div class="hud-row"><span class="err-mark"></span><span class="hud-title">无法录音</span></div>' +
          '<p class="hud-hint">系统未允许使用麦克风。打开权限后重试。</p>',
        "err"
      );
      return;
    }
    if (screen === "fail-field") {
      showHud(
        '<div class="hud-row"><span class="err-mark"></span><span class="hud-title">没有可填入的输入框</span></div>' +
          '<p class="hud-hint">整理已完成，但当前没有能接收文字的位置。请点进一个输入框后再试或重录。</p>',
        "err wide"
      );
      return;
    }
    hideHud();
  }

  function renderScreen() {
    const isReader = screen === "fail-field";
    appStack.classList.toggle("hidden", isReader);
    appAi.classList.toggle("hidden", isReader);
    appReader.classList.toggle("hidden", !isReader);
    spokenNote.textContent =
      "口语原文（产品不展示，仅供对照）：" + SCENE[scene].spoken;

    composer.classList.toggle("unfocused", screen === "fail-mic");
    composer.classList.toggle("focused", screen !== "fail-mic" && screen !== "fail-field");
    inputBox.setAttribute("contenteditable", screen === "success" ? "true" : "false");

    if (screen === "success") {
      sendNote.textContent = "发送键留给用户。SayClear 填入后不会替你按它。要改字，直接在这个输入框里改。";
      filledText = sceneText();
      setFilled(filledText, true);
    } else if (screen === "fail-mic") {
      sendNote.textContent = "发送键留给用户。SayClear 不会代发。";
      setPlaceholder(false);
    } else {
      sendNote.textContent = "发送键留给用户。SayClear 不会代发。要改字，填入后直接在输入框里改。";
      setPlaceholder(true);
    }

    renderHud();
  }

  function go(next) {
    screen = next;
    body.setAttribute("data-screen", next);
    document.querySelectorAll(".screens [data-go]").forEach(function (btn) {
      btn.classList.toggle("is-on", btn.getAttribute("data-go") === next);
    });
    document.querySelectorAll(".notes article").forEach(function (el) {
      el.classList.toggle("is-on", el.getAttribute("data-for") === next);
    });
    renderScreen();
    try {
      history.replaceState(null, "", "?screen=" + encodeURIComponent(next) + "&scene=" + encodeURIComponent(scene));
    } catch (e) {}
  }

  function setScene(id) {
    scene = id;
    filledText = SCENE[id].text;
    body.setAttribute("data-scene", id);
    document.querySelectorAll(".scene-toggle [data-scene]").forEach(function (btn) {
      btn.classList.toggle("is-on", btn.getAttribute("data-scene") === id);
    });
    renderScreen();
    try {
      history.replaceState(null, "", "?screen=" + encodeURIComponent(screen) + "&scene=" + encodeURIComponent(scene));
    } catch (e) {}
  }

  document.querySelectorAll(".screens [data-go]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      go(btn.getAttribute("data-go"));
    });
  });

  document.querySelectorAll(".scene-toggle [data-scene]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      setScene(btn.getAttribute("data-scene"));
    });
  });

  sendBtn.addEventListener("click", function () {
    sendNote.textContent = "这是用户自己点的发送。SayClear 不会代发——本原型不真正发出。";
  });

  const allowed = {
    flow: 1,
    idle: 1,
    record: 1,
    process: 1,
    success: 1,
    "fail-mic": 1,
    "fail-field": 1,
  };
  const params = new URLSearchParams(location.search);
  const start = allowed[params.get("screen")] ? params.get("screen") : "flow";
  const startScene = params.get("scene");
  if (startScene === "b" || startScene === "c") {
    scene = startScene;
    filledText = SCENE[startScene].text;
    body.setAttribute("data-scene", startScene);
    document.querySelectorAll(".scene-toggle [data-scene]").forEach(function (btn) {
      btn.classList.toggle("is-on", btn.getAttribute("data-scene") === startScene);
    });
  }
  go(start);
})();
