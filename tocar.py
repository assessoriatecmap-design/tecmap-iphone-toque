# -*- coding: utf-8 -*-
"""TOQUE DE VERDADE NO SAFARI DO IPHONE (simulador no Mac do GitHub Actions). TECMAP, 27/09/2026.

Por que existe: o teste no Chrome clica pelo JavaScript e não vê o que o iPhone faz com o dedo. No iPhone, o toque num
div, span ou li só vira «click» que sobe até o document se o elemento parecer clicável. Aqui cada toque é um toque na
tela (XCUITest, `mobile: tap` numa coordenada), e uma sonda na página anota se o dedo chegou (touchstart) e se virou
clique no alvo.

  1. controle: página local com um div SEM cursor:pointer, um COM e um botão. Prova que o toque é de dedo e mostra a
     regra do iPhone.
  2. o site: entra em cada papel pelo formulário (toque no «Entrar»), toca na câmera do cadastro (espera o menu de foto
     do iOS), anda pelas telas tocando nos elementos de navegação (div, span e li primeiro) e, no papel de professor,
     marca F e P na chamada e devolve a chamada da demonstração ao retrato de antes (conferido depois).

Variáveis: URL_TESTE, LOGINS_JSON ({"admin": "...", "prof": "...", "aluno": "..."}), SENHA_DEMO, UDID, SIM_IOS, SIM_NOME.
Saída: saida/resultado.json, saida/NN-*.png e o resumo da execução. Sai 1 se algum toque esperado falhou.
"""
import json
import os
import re
import sys
import time
import traceback

from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy

URL = os.environ.get("URL_TESTE", "").rstrip("/")
LOGINS = json.loads(os.environ.get("LOGINS_JSON") or "{}")
SENHA = os.environ.get("SENHA_DEMO", "")
OUT = "saida"
os.makedirs(OUT, exist_ok=True)
R = {"aparelho": "%s, iOS %s" % (os.environ.get("SIM_NOME"), os.environ.get("SIM_IOS")), "controle": [], "papeis": {},
     "falhas": [], "avisos": []}
N = [0]

# navegação e abrir detalhe: nada disso grava. O resto (salvar, excluir, sair, pagar, gerar, IA, WhatsApp) não se toca.
NAVEGA = re.compile(r"^(go|abrirTurma|abrirTurmaNaAba|abrirTarefa|abrirAluno|abrirMaterial|turmaTab|ptTab|abrirAjuda|"
                    r"mapaAlterna|abrirConquista|openLead|scAbrirAluno|dcAbrirPasta|verDocsDe|irChamadaDeHoje)\(")
NUNCA = re.compile(r"sair|excluir|apagar|salvar|enviar|pagar|fechar|gerar|emitir|matricula|openChat|contato|editar|"
                   r"verComo|Senha|abrirPagina|voltar|abrirLinkExterno|lancar", re.I)
ARRISCADOS = ("DIV", "SPAN", "LI")   # sem onclick, só estes dependem do cursor:pointer no iPhone


def falha(m):
    R["falhas"].append(m)
    print("❌ " + m, flush=True)


def ok(m):
    print("✅ " + m, flush=True)


def aviso(m):
    R["avisos"].append(m)
    print("⚠️ " + m, flush=True)


opts = XCUITestOptions()
opts.udid = os.environ["UDID"]
opts.platform_version = os.environ["SIM_IOS"]
opts.device_name = os.environ["SIM_NOME"]
opts.browser_name = "Safari"
opts.new_command_timeout = 900
opts.set_capability("appium:wdaLaunchTimeout", 480000)
opts.set_capability("appium:wdaConnectionTimeout", 480000)
opts.set_capability("appium:webviewConnectTimeout", 60000)
# o fluxo já ligou o iPhone sem janela; sem isto o Appium o reinicia com janela e espera de novo (27/09: 2 min perdidos)
opts.set_capability("appium:isHeadless", True)
opts.set_capability("appium:simulatorStartupTimeout", 300000)
# a 1ª abertura do Safari num iPhone recém-ligado passa de 30 s (27/09); o fluxo aquece antes e aqui tenta mais vezes
opts.set_capability("appium:wdaStartupRetries", 4)
opts.set_capability("appium:wdaStartupRetryInterval", 15000)
print("abrindo o Safari no", R["aparelho"], flush=True)
drv = webdriver.Remote("http://127.0.0.1:4723", options=opts)
drv.set_script_timeout(45)   # 27/09: o padrão do Appium é 3 ms e o retrato da chamada (fetch) caía antes de começar
WEB = [drv.current_context]
print("contexto da página:", WEB[0], flush=True)


def web():
    try:
        if not WEB[0] or WEB[0] == "NATIVE_APP":
            raise ValueError("sem contexto de página")
        drv.switch_to.context(WEB[0])
    except Exception:
        ws = [c for c in drv.contexts if c != "NATIVE_APP"]
        WEB[0] = ws[-1]
        drv.switch_to.context(WEB[0])


def nativo():
    drv.switch_to.context("NATIVE_APP")


def js(codigo, *args):
    web()
    return drv.execute_script(codigo, *args)


def abrir(url):
    web()
    drv.get(url)
    WEB[0] = drv.current_context


def foto(nome):
    N[0] += 1
    try:
        drv.get_screenshot_as_file(os.path.join(OUT, "%02d-%s.png" % (N[0], re.sub(r"[^a-z0-9]+", "-", nome.lower())[:48])))
    except Exception as e:
        aviso("foto %s: %s" % (nome, str(e).splitlines()[0][:120]))


def tela():
    return js("return (document.querySelector('.screen.on')||{}).id||'';")


# 27/09: depois do login o iOS abre «Save Password?» POR CIMA da página, e nenhum toque chega nela (aluno e professor:
# 0 de 17). Quem usa de verdade toca em «Not Now»; o roteiro faz o mesmo antes de seguir.
AVISOS_DO_IOS = "label IN {'Not Now', 'Agora Não', 'Agora não', 'Never for This Website', 'Nunca Neste Site'}"


def fechar_avisos_do_ios():
    fechou = 0
    nativo()
    for _ in range(3):
        b = [x for x in drv.find_elements(AppiumBy.IOS_PREDICATE, AVISOS_DO_IOS) if x.get_attribute("label") in ("Not Now", "Agora Não", "Agora não")]
        if not b:
            break
        b[0].click()
        fechou += 1
        time.sleep(1.2)
    web()
    if fechou:
        print("   (fechei %d aviso(s) do iOS: «Save Password?»)" % fechou, flush=True)
    return fechou


SONDA = """if (!window.__sondaOk) { window.__sondaOk = 1; window.__sonda = [];
  ['touchstart', 'touchend', 'click'].forEach(function (t) {
    document.addEventListener(t, function (e) {
      var el = e.target, m = !!(el && el.closest && el.closest('[data-alvo-teste]'));
      window.__sonda.push(t + (m ? ':alvo' : ':fora'));
    }, true);
  }); }
return 1;"""


def calibrar():
    """Um quadrado de referência numa posição conhecida da página; o iPhone diz onde ele está na tela."""
    js("""var d = document.getElementById('__cal');
      if (!d) { d = document.createElement('div'); d.id = '__cal'; d.setAttribute('role', 'button');
        d.setAttribute('aria-label', 'tecmapcalibra'); d.textContent = '.';
        d.style.cssText = 'position:fixed;left:40px;top:120px;width:100px;height:100px;z-index:2147483647;' +
          'background:rgba(255,0,0,0.03);color:transparent'; document.body.appendChild(d); }
      return 1;""")
    time.sleep(0.6)
    nativo()
    r = None
    for _ in range(5):
        achados = drv.find_elements(AppiumBy.IOS_PREDICATE, "label == 'tecmapcalibra' OR name == 'tecmapcalibra'")
        if achados:
            r = achados[0].rect
            break
        time.sleep(0.8)
    js("var d = document.getElementById('__cal'); if (d) d.remove(); return 1;")
    if not r:
        raise RuntimeError("calibração: o iPhone não achou o quadrado de referência")
    esc = r["width"] / 100.0
    return r["x"] - 40 * esc, r["y"] - 120 * esc, esc


def tocar(achar, nome, esperar=1.2, _de_novo=False):
    """Toca com o dedo no centro do elemento que `achar` (corpo de função JS) devolve. Devolve o que a sonda viu.
    Se o dedo não chegou na página e havia um aviso do iOS por cima, fecha o aviso e toca de novo (uma vez)."""
    t = _tocar(achar, nome, esperar)
    if t and not t["dedo"] and not _de_novo and fechar_avisos_do_ios():
        return tocar(achar, nome, esperar, _de_novo=True)
    return t


def _tocar(achar, nome, esperar):
    info = js("""document.querySelectorAll('[data-alvo-teste]').forEach(function (e) { e.removeAttribute('data-alvo-teste'); });
      var el = (function () { %s })(); if (!el) return null;
      el.setAttribute('data-alvo-teste', '1'); el.scrollIntoView({block: 'center', inline: 'center'});
      return {tag: el.tagName, oc: el.getAttribute('data-onclick') || '', cursor: getComputedStyle(el).cursor,
              tela: (document.querySelector('.screen.on') || {}).id || ''};""" % achar)
    if not info:
        return None
    time.sleep(0.5)
    ox, oy, esc = calibrar()
    b = js("""var el = document.querySelector('[data-alvo-teste]'); var b = el.getBoundingClientRect();
      window.__sonda = []; window.__cliques = [];
      return {x: b.left + b.width / 2, y: b.top + Math.min(b.height / 2, 22), w: b.width, h: b.height};""")
    x, y = ox + b["x"] * esc, oy + b["y"] * esc
    nativo()
    drv.execute_script("mobile: tap", {"x": x, "y": y})
    time.sleep(esperar)
    depois = js("return {sonda: window.__sonda || [], cliques: window.__cliques || [], "
                "tela: (document.querySelector('.screen.on') || {}).id || ''};")
    info.update({"nome": nome, "x": round(x), "y": round(y), "sonda": depois["sonda"], "cliques": depois["cliques"],
                 "tela_depois": depois["tela"], "dedo": "touchstart:alvo" in depois["sonda"],
                 "clique": "click:alvo" in depois["sonda"]})
    return info


# ---------------------------------------------------------------- 1. controle
def controle():
    abrir("http://127.0.0.1:8765/controle.html")
    time.sleep(2)
    foto("controle")
    for rodada in ("sem-sonda", "com-sonda"):
        if rodada == "com-sonda":
            js(SONDA)
        for alvo in ("sem", "com", "bt"):
            t = tocar("return document.getElementById('%s');" % alvo, alvo)
            chegou = alvo in (t or {}).get("cliques", [])
            R["controle"].append({"rodada": rodada, "alvo": alvo, "clique_no_document": chegou,
                                  "dedo": (t or {}).get("dedo"), "sonda": (t or {}).get("sonda")})
            print("   controle %-9s %-3s → clique no document: %s | sonda: %s" % (rodada, alvo, chegou, (t or {}).get("sonda")), flush=True)
    com = [c for c in R["controle"] if c["rodada"] == "com-sonda"]
    if all(c["dedo"] for c in com):
        ok("controle: o toque é de dedo (touchstart chegou nos três)")
    else:
        falha("controle: o toque NÃO chegou como dedo em todos: o instrumento não prova nada")
    if all(c["clique_no_document"] for c in R["controle"] if c["alvo"] in ("com", "bt")):
        ok("controle: div COM cursor:pointer e botão viram clique no document")
    else:
        falha("controle: div com cursor:pointer ou botão não virou clique")
    sem = [c["clique_no_document"] for c in R["controle"] if c["alvo"] == "sem"]
    R["regra_do_iphone_reproduzida"] = not any(sem)
    print("   div SEM cursor:pointer virou clique? %s (a regra do iPhone %s)" % (
        sem, "reproduzida" if not any(sem) else "NÃO apareceu neste iOS"), flush=True)


# ---------------------------------------------------------------- 2. o site
def entrar(papel):
    abrir(URL + "/")
    time.sleep(2)
    js("try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} return 1;")
    abrir(URL + "/?t=%d" % int(time.time()))
    time.sleep(4)
    js(SONDA)
    web()
    e = drv.find_element(AppiumBy.CSS_SELECTOR, "#loginEmail")
    e.clear()
    e.send_keys(LOGINS[papel])
    s = drv.find_element(AppiumBy.CSS_SELECTOR, "#loginSenha")
    s.clear()
    s.send_keys(SENHA)
    js("if (document.activeElement) document.activeElement.blur(); return 1;")
    time.sleep(1)
    t = tocar("return document.getElementById('btEntrar');", "Entrar", esperar=2)
    fim = time.time() + 30
    while time.time() < fim:
        if js("return !!(window.SESSAO && window.SESSAO.token);"):
            break
        time.sleep(1)
    else:
        falha("%s: o toque no Entrar não entrou (sonda: %s)" % (papel, (t or {}).get("sonda")))
        foto(papel + "-nao-entrou")
        return False
    time.sleep(2)
    ok("%s: entrou pelo toque no Entrar" % papel)
    time.sleep(1.5)
    fechar_avisos_do_ios()
    foto(papel + "-entrou")
    return True


def testar_foto(papel, reg):
    if tela() != "s-completar":
        return
    t = tocar("return document.getElementById('ccFoto');", "câmera do cadastro (div)", esperar=2.5)
    nativo()
    # o simulador está em inglês; a página fala português («Escolher foto»), então o rótulo exato separa o menu do iOS
    rotulos = sorted(set(x.get_attribute("label") or "" for x in drv.find_elements(
        AppiumBy.IOS_PREDICATE, "label IN {'Photo Library', 'Take Photo', 'Choose File', 'Choose Files', "
                                "'Take Photo or Video', 'Fototeca', 'Tirar Foto', 'Escolher Arquivo'}")))
    foto(papel + "-menu-da-foto")
    reg["foto"] = {"toque": t, "menu_do_ios": rotulos}
    if t and t["clique"] and rotulos:
        ok("%s: tocar na câmera (div) abriu o menu de foto do iPhone: %s" % (papel, rotulos))
    else:
        falha("%s: tocar na câmera não abriu o menu de foto (clique: %s, menu: %s)" % (papel, (t or {}).get("clique"), rotulos))
    # fecha o menu sem escolher nada
    for _ in range(3):
        nativo()
        if not drv.find_elements(AppiumBy.IOS_PREDICATE, "label IN {'Photo Library', 'Choose File', 'Take Photo'}"):
            break
        fechar = drv.find_elements(AppiumBy.IOS_PREDICATE, "label IN {'Cancel', 'Cancelar'}")
        if fechar:
            fechar[0].click()
        else:
            drv.execute_script("mobile: tap", {"x": 20, "y": 70})
        time.sleep(1.5)
    # só nesta aba do teste: segue para o início do papel sem gravar o cadastro (igual ao csp-local.py)
    js("window.precisaCompletar = function () { return false; };"
       "go(window.SESSAO.papel === 'professor' ? 'prof-home' : (window.SESSAO.papel === 'admin' ? 'admin-home' : 'home'));"
       "return 1;")
    time.sleep(2)


COLHER = """return Array.from(document.querySelectorAll('[data-onclick]')).filter(function (e) {
  if (e.offsetParent === null) return false; var b = e.getBoundingClientRect(); return b.width > 8 && b.height > 8;
}).map(function (e) { return {oc: e.getAttribute('data-onclick'), tag: e.tagName}; });"""
ACHAR_OC = """var alvo = %s; return Array.from(document.querySelectorAll('[data-onclick]')).filter(function (e) {
  return e.getAttribute('data-onclick') === alvo && e.offsetParent !== null; })[0] || null;"""


def andar(papel, reg, limite=24):
    tentados, fila = set(), []

    def colher():
        agora = tela()
        for it in js(COLHER) or []:
            oc = it["oc"]
            if oc in tentados or any(oc == f[0] for f in fila) or not NAVEGA.match(oc) or NUNCA.search(oc):
                continue
            fila.append((oc, agora, it["tag"]))
        fila.sort(key=lambda f: 0 if f[2] in ARRISCADOS else 1)

    colher()
    inicio = tela()
    while fila and len(tentados) < limite:
        oc, origem, tag = fila.pop(0)
        tentados.add(oc)
        if tela() != origem and origem:
            js("go(arguments[0]); return 1;", origem[2:])
            time.sleep(1.2)
        t = tocar(ACHAR_OC % json.dumps(oc), oc)
        if not t:
            continue
        esperado = ""
        m = re.match(r"^go\('([\w-]+)'", oc)
        if m:
            esperado = "s-" + m.group(1)
        t["esperado"] = esperado
        reg["toques"].append(t)
        rotulo = "%s %s %s" % (papel, t["tag"].lower(), oc[:60])
        if not t["dedo"]:
            aviso("%s: o dedo não chegou no alvo (coordenada %s,%s; sonda %s)" % (rotulo, t["x"], t["y"], t["sonda"]))
        elif not t["clique"]:
            falha("%s: o dedo chegou e NÃO virou clique" % rotulo)
        elif esperado and t["tela_depois"] != esperado:
            aviso("%s: virou clique, mas a tela foi %s (esperava %s)" % (rotulo, t["tela_depois"], esperado))
        else:
            print("   ✓ %s → %s" % (rotulo, t["tela_depois"]), flush=True)
        if len(reg["toques"]) <= 10 or t["tag"] in ARRISCADOS and len(reg["toques"]) <= 18:
            foto("%s-%s" % (papel, oc[:30]))
        colher()
    if inicio:
        js("go(arguments[0]); return 1;", inicio[2:])
        time.sleep(1)


def chamada(reg):
    """Professor: abre a turma e a aba Frequência pelo toque, marca F e P, e devolve a chamada da demonstração."""
    js("go('prof-turmas'); return 1;")
    time.sleep(1.5)
    t1 = tocar("return Array.from(document.querySelectorAll('[data-onclick^=\"abrirTurma\"]')).filter(function (e) {"
               " return e.offsetParent !== null; })[0] || null;", "turma (lista de turmas)", esperar=2)
    t2 = tocar("return Array.from(document.querySelectorAll('[data-onclick=\"ptTab(this,\\'freq\\')\"]')).filter(function (e) {"
               " return e.offsetParent !== null; })[0] || null;", "aba Frequência", esperar=1.5)
    reg["chamada"] = {"turma": t1, "aba": t2}
    foto("prof-frequencia")
    if not (t1 and t1["clique"] and t2 and t2["clique"]):
        falha("prof: abrir a turma e a aba Frequência pelo toque (turma: %s, aba: %s)" % ((t1 or {}).get("clique"), (t2 or {}).get("clique")))
        return
    ok("prof: turma e aba Frequência abertas pelo toque (dois div)")
    if not js("return !!document.querySelector('#freqList button.f:not([disabled])');"):
        aviso("prof: a chamada de hoje não tem aluno para marcar (ou está fechada): P/F não tocado")
        return
    web()
    antes = drv.execute_async_script("""var cb = arguments[arguments.length - 1];
      fetch('/api/dados', {headers: {Authorization: 'Bearer ' + window.SESSAO.token}}).then(function (r) { return r.json(); })
      .then(function (d) { window.__origCham = d.wn_chamadas || {}; cb(JSON.stringify(window.__origCham)); })
      .catch(function (e) { cb('ERRO ' + e); });""")
    if antes.startswith("ERRO"):
        aviso("prof: sem o retrato da chamada (%s): P/F não tocado para não sujar a demonstração" % antes[:80])
        return
    tf = tocar("return document.querySelector('#freqList button.f');", "F (falta)", esperar=1.5)
    f_on = js("return !!document.querySelector('#freqList button.f.on');")
    foto("prof-marcou-f")
    tp = tocar("return document.querySelector('#freqList button.p');", "P (presente)", esperar=1.5)
    p_on = js("return !!document.querySelector('#freqList button.p.on');")
    reg["chamada"].update({"F": tf, "F_marcado": f_on, "P": tp, "P_marcado": p_on})
    if tf and tf["clique"] and f_on and tp and tp["clique"] and p_on:
        ok("prof: chamada P/F pelo toque (F marcou, P marcou de volta)")
    else:
        falha("prof: chamada P/F pelo toque (F: %s/%s, P: %s/%s)" % ((tf or {}).get("clique"), f_on, (tp or {}).get("clique"), p_on))
    time.sleep(6)   # o app grava 400 ms depois; espera a gravação terminar antes de devolver o retrato
    web()
    volta = drv.execute_async_script("""var cb = arguments[arguments.length - 1], h = {Authorization: 'Bearer ' + window.SESSAO.token,
      'Content-Type': 'application/json'};
      fetch('/api/dados', {method: 'PUT', headers: h, body: JSON.stringify({chave: 'wn_chamadas', valor: window.__origCham})})
      .then(function (r) { return r.status; })
      .then(function (s) { return fetch('/api/dados', {headers: h}).then(function (r) { return r.json(); })
        .then(function (d) { cb(JSON.stringify({status: s, agora: d.wn_chamadas || {}})); }); })
      .catch(function (e) { cb(JSON.stringify({status: 'ERRO ' + e})); });""")
    v = json.loads(volta)
    igual = json.dumps(v.get("agora"), sort_keys=True) == json.dumps(json.loads(antes), sort_keys=True)
    reg["chamada"]["devolvida"] = {"status": v.get("status"), "igual_ao_retrato": igual}
    if igual:
        ok("prof: chamada da demonstração devolvida ao retrato de antes (conferido pela leitura)")
    else:
        falha("prof: a chamada da demonstração NÃO voltou ao retrato (status %s)" % v.get("status"))


def papel(p):
    reg = {"toques": []}
    R["papeis"][p] = reg
    try:
        if not entrar(p):
            return
        testar_foto(p, reg)
        if p == "prof":
            chamada(reg)
            js("go('prof-home'); return 1;")
            time.sleep(1.5)
        andar(p, reg)
    except Exception as e:
        falha("%s: o roteiro quebrou: %s" % (p, str(e).splitlines()[0][:200]))
        traceback.print_exc()
        foto(p + "-quebrou")
    finally:
        try:
            js("try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} return 1;")
        except Exception:
            pass


try:
    controle()
    if URL:
        for p in ("aluno", "prof", "admin"):
            if p in LOGINS:
                papel(p)
except Exception as e:
    falha("o roteiro quebrou: %s" % str(e).splitlines()[0][:200])
    traceback.print_exc()
finally:
    try:
        drv.quit()
    except Exception:
        pass

todos = [t for r in R["papeis"].values() for t in r.get("toques", [])]
arris = [t for t in todos if t["tag"] in ARRISCADOS]
R["numeros"] = {"toques": len(todos), "div_span_li": len(arris), "viraram_clique": sum(1 for t in todos if t["clique"]),
                "div_span_li_viraram_clique": sum(1 for t in arris if t["clique"]),
                "dedo_nao_chegou": sum(1 for t in todos if not t["dedo"])}
json.dump(R, open(os.path.join(OUT, "resultado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
linhas = ["## iPhone: toque de verdade (%s)" % R["aparelho"], "",
          "| | |", "|---|---|",
          "| regra do iPhone reproduzida no controle | %s |" % R.get("regra_do_iphone_reproduzida"),
          "| toques no site | %d |" % len(todos),
          "| div/span/li tocados | %d |" % len(arris),
          "| div/span/li que viraram clique | %d |" % R["numeros"]["div_span_li_viraram_clique"],
          "| toques em que o dedo não chegou | %d |" % R["numeros"]["dedo_nao_chegou"], ""]
linhas += ["- ❌ " + f for f in R["falhas"]] + ["- ⚠️ " + a for a in R["avisos"]]
if os.environ.get("GITHUB_STEP_SUMMARY"):
    open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8").write("\n".join(linhas) + "\n")
print("\n".join(linhas))
sys.exit(1 if R["falhas"] else 0)
