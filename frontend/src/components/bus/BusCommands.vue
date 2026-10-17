<template>
  <div class="cmds">
    <div class="banner warn">
      <Icon :path="mdiAlertOutline" :size="20" />
      <div>
        <b>{{ t("warnTitle") }}</b> {{ t("warnText") }}
      </div>
    </div>

    <div class="grid cmd-grid mt">
      <!-- builder -->
      <Card :title="t('compose')" :icon="mdiConsoleLine" :subtitle="t('composeSub')">
        <div class="row wrap between">
          <div class="btn-group">
            <button :class="{ active: mode === '16' }" :title="t('m16Hint')" @click="mode = '16'">16 Bit</button>
            <button :class="{ active: mode === '24' }" :title="t('m24Hint')" @click="mode = '24'">24 Bit</button>
            <button :class="{ active: mode === 'raw' }" @click="mode = 'raw'">{{ t("raw") }}</button>
          </div>
          <label class="field line-field">
            <span>{{ t("line") }}</span>
            <select v-model.number="line">
              <option v-for="l in lineIds" :key="l" :value="l">{{ t("line") }} {{ l }}</option>
            </select>
          </label>
        </div>
        <div class="small muted mt">{{ mode === "16" ? t("m16Hint") : mode === "24" ? t("m24Hint") : t("rawHint") }}</div>

        <!-- 16 bit -->
        <template v-if="mode === '16'">
          <div class="section-title">{{ t("addressing") }}</div>
          <div class="btn-group wrap-group">
            <button v-for="a in at16Opts" :key="a.id" :class="{ active: at16 === a.id }" @click="at16 = a.id">{{ a.label }}</button>
          </div>
          <div class="form-grid mt">
            <template v-if="at16 === 'short'">
              <label class="field">
                <span>{{ t("shortAddr") }} (0–63)</span>
                <input v-model.number="shortAddr" type="number" min="0" max="63" />
              </label>
              <label class="field">
                <span>{{ t("pickDevice") }}</span>
                <select :value="deviceAtAddr?.id ?? ''" @change="pickDevice(($event.target as HTMLSelectElement).value)">
                  <option value="">–</option>
                  <option v-for="d in lineDevices" :key="d.id" :value="d.id">A{{ d.address }} · {{ d.name }}</option>
                </select>
              </label>
            </template>
            <label v-else-if="at16 === 'group'" class="field">
              <span>{{ t("group") }} (0–15)</span>
              <input v-model.number="groupAddr" type="number" min="0" max="15" />
            </label>
            <template v-else-if="at16 === 'special'">
              <label class="field">
                <span>{{ t("specialCmd") }}</span>
                <select v-model.number="special">
                  <option v-for="s in SPECIAL_PICK" :key="s" :value="s">0x{{ hex2(s) }} · {{ SPECIAL_COMMANDS_16[s] }}</option>
                </select>
              </label>
              <label class="field">
                <span>{{ t("dataByte") }} (0–255)</span>
                <input v-model.number="specialData" type="number" min="0" max="255" />
              </label>
            </template>
          </div>

          <template v-if="at16 !== 'special'">
            <div class="section-title">{{ t("selector") }}</div>
            <div class="btn-group">
              <button :class="{ active: sel16 === 'cmd' }" @click="sel16 = 'cmd'">{{ t("selCmd") }}</button>
              <button :class="{ active: sel16 === 'dapc' }" @click="sel16 = 'dapc'">{{ t("selDapc") }}</button>
            </div>

            <div v-if="sel16 === 'dapc'" class="field mt">
              <span class="row between"><span>{{ t("level") }}</span><span class="mono">{{ dapcLevel }} ≙ {{ dapcLevel === 255 ? "MASK" : levelPct(dapcLevel) }}</span></span>
              <div class="row">
                <input v-model.number="dapcLevel" type="range" min="0" max="254" class="grow" />
                <input v-model.number="dapcLevel" type="number" min="0" max="255" class="num" />
              </div>
            </div>

            <div v-else class="form-grid mt">
              <label class="field cmd-field">
                <span>{{ t("command") }}</span>
                <select v-model="cmd16">
                  <optgroup v-for="g in groups16" :key="g.cat" :label="g.label">
                    <option v-for="p in g.items" :key="p.op" :value="String(p.op)">{{ pickLabel16(p) }}</option>
                  </optgroup>
                  <option value="custom">{{ t("customOpcode") }}</option>
                </select>
              </label>
              <label v-if="pick16?.param" class="field">
                <span>{{ pick16.param === "scene" ? t("sceneN") : t("groupN") }} (0–15)</span>
                <input v-model.number="param16" type="number" min="0" max="15" />
              </label>
              <label v-if="cmd16 === 'custom'" class="field">
                <span>Opcode (0–255)</span>
                <input v-model.number="custom16" type="number" min="0" max="255" />
              </label>
            </div>
          </template>
        </template>

        <!-- 24 bit -->
        <template v-if="mode === '24'">
          <div class="section-title">{{ t("addressing") }}</div>
          <div class="btn-group wrap-group">
            <button v-for="a in at24Opts" :key="a.id" :class="{ active: at24 === a.id }" @click="at24 = a.id">{{ a.label }}</button>
          </div>
          <div class="form-grid mt">
            <label v-if="at24 === 'short'" class="field">
              <span>{{ t("shortAddr") }} (0–63)</span>
              <input v-model.number="short24" type="number" min="0" max="63" />
            </label>
            <label v-if="at24 === 'group'" class="field">
              <span>{{ t("deviceGroup") }} (0–31)</span>
              <input v-model.number="group24" type="number" min="0" max="31" />
            </label>
            <label class="field">
              <span>{{ t("instance") }}</span>
              <select v-model="inst">
                <option value="device">{{ t("instDevice") }} (0xFE)</option>
                <option value="number">{{ t("instNumber") }}</option>
                <option value="type">{{ t("instType") }}</option>
                <option value="all">{{ t("instAll") }} (0xFF)</option>
              </select>
            </label>
            <label v-if="inst === 'number' || inst === 'type'" class="field">
              <span>{{ inst === "number" ? t("instNumber") : t("instType") }} (0–31)</span>
              <input v-model.number="instNum" type="number" min="0" max="31" />
            </label>
          </div>
          <div class="form-grid mt">
            <label class="field cmd-field">
              <span>{{ t("command") }}</span>
              <select v-model="cmd24">
                <optgroup v-for="g in groups24" :key="g.cat" :label="g.label">
                  <option v-for="p in g.items" :key="p.op" :value="String(p.op)">0x{{ hex2(p.op) }} · {{ DEVICE_COMMANDS[p.op] }}</option>
                </optgroup>
                <option value="custom">{{ t("customOpcode") }}</option>
              </select>
            </label>
            <label v-if="cmd24 === 'custom'" class="field">
              <span>Opcode (0–255)</span>
              <input v-model.number="custom24" type="number" min="0" max="255" />
            </label>
          </div>
        </template>

        <!-- raw -->
        <template v-if="mode === 'raw'">
          <label class="field mt">
            <span>{{ t("rawLabel") }}</span>
            <textarea v-model="rawText" rows="3" spellcheck="false" :placeholder="t('rawPh')"></textarea>
            <span class="hint">{{ t("rawHint2") }}</span>
          </label>
        </template>

        <!-- DTR0 / send twice -->
        <div v-if="mode !== 'raw' && (needsDtr || isConfigSel)" class="opts mt">
          <label v-if="needsDtr" class="check">
            <input v-model="useDtr0" type="checkbox" />
            {{ t("setDtr0") }}
            <input v-model.number="dtr0" type="number" min="0" max="255" class="num" :disabled="!useDtr0" @click.stop />
          </label>
          <div v-if="needsDtr && useDtr0 && dtrHint" class="hint small faint">{{ dtrHint }}</div>
          <label v-if="isConfigSel" class="check">
            <input v-model="sendTwice" type="checkbox" />{{ t("sendTwice") }}
          </label>
        </div>

        <!-- quick queries -->
        <template v-if="mode === '16' && at16 !== 'special'">
          <div class="section-title">{{ t("quick") }}</div>
          <div class="row wrap quick">
            <button v-for="q in QUICK" :key="q" class="chip clickable" :disabled="sending" @click="quickQuery(q)">
              {{ GEAR_COMMANDS[q].replace("QUERY ", "") }}
            </button>
          </div>
        </template>

        <!-- preview -->
        <div class="section-title">{{ t("preview") }}</div>
        <div v-if="built.error" class="banner err small">
          <Icon :path="mdiAlertCircle" :size="18" />
          <div>{{ built.error }}</div>
        </div>
        <div v-else class="preview">
          <div v-for="(fr, i) in built.frames" :key="i" class="pv-row">
            <span class="kbadge" :style="kindStyle(builtDesc[i]?.kind)">{{ kindLabel(builtDesc[i]?.kind, lang) }}</span>
            <span class="mono pv-hex">{{ bytesHex(fr) }}</span>
            <span class="mono faint small pv-bin">{{ fr.map(bin8).join(" ") }}</span>
            <span class="small pv-text">{{ builtDesc[i]?.text }}</span>
          </div>
          <div class="row wrap mt-s">
            <span class="chip" :class="levelMeta.chip">{{ levelMeta.label }}</span>
            <span class="small muted">{{ levelMeta.hint }}</span>
          </div>
        </div>

        <template #footer>
          <button class="btn" :class="{ danger: sendLevel === 'danger' }" :disabled="sending || !!built.error || !built.frames.length || !online" @click="sendBuilt">
            <span v-if="sending" class="spinner mini light"></span>
            <Icon v-else :path="mdiSend" :size="18" />
            {{ t("send") }}
          </button>
        </template>
      </Card>

      <!-- result -->
      <Card :title="t('result')" :icon="mdiReply" :icon-class="last ? (last.error ? 'err' : 'ok') : 'off'">
        <Empty v-if="!last" :icon="mdiConsoleLine" :text="t('noResult')" />
        <template v-else>
          <div class="row wrap">
            <span class="chip" :class="last.error ? 'err' : 'ok'">{{ last.error ? t("error") : t("sent") }}</span>
            <span class="small muted">{{ fmtMs(last.ts, true, lang) }} · {{ last.ms }} ms · {{ t("line") }} {{ last.line }}</span>
          </div>
          <div class="preview mt">
            <div v-for="(fr, i) in last.frames" :key="i" class="pv-row">
              <span class="mono pv-hex">{{ bytesHex(fr) }}</span>
              <span class="small pv-text">{{ lastDesc[i]?.text }}</span>
            </div>
          </div>
          <div v-if="last.error" class="banner err small mt">
            <Icon :path="mdiAlertCircle" :size="18" />
            <div>{{ last.error }}</div>
          </div>
          <template v-else>
            <div class="section-title">{{ t("answers") }}</div>
            <div v-if="!last.answers.length" class="banner small" :class="last.query ? 'warn' : 'info'">
              <Icon :path="mdiInformationOutline" :size="18" />
              <div>{{ last.query ? t("noAnswerQuery") : t("noAnswerCmd") }}</div>
            </div>
            <div v-else class="answers">
              <div v-for="(v, i) in last.answers" :key="i" class="ans">
                <template v-if="validByte(v)">
                  <div class="ans-big mono">{{ v }}</div>
                  <div class="small mono muted">0x{{ hex2(v) }}</div>
                  <div class="small mono muted">0b{{ bin8(v) }}</div>
                </template>
                <template v-else>
                  <div class="ans-big mono faint">–</div>
                  <div class="small muted">{{ t("noAnswerCode", { v: String(v) }) }}</div>
                </template>
              </div>
            </div>
            <template v-if="lastExplain">
              <div class="banner info small mt">
                <Icon :path="mdiLightbulbOnOutline" :size="18" />
                <div><b>{{ shortName(last.queryName) }}:</b> {{ lastExplain.summary }}</div>
              </div>
              <div v-if="lastExplain.bits" class="status-bits mt">
                <div v-for="b in lastExplain.bits" :key="b.bit" class="sbit" :class="{ on: b.set, err: b.set && b.severity === 'err' }">
                  <span class="mono small bitno">{{ b.bit }}</span>
                  <span class="dot" :class="b.set ? (b.severity === 'err' ? 'err' : b.severity === 'warn' ? 'warn' : 'ok') : ''"></span>
                  <span class="small">{{ b.label }}</span>
                </div>
              </div>
            </template>
          </template>
        </template>
      </Card>
    </div>

    <!-- history -->
    <Card :title="t('history')" :icon="mdiHistory" :subtitle="t('historySub')" class="mt" flush>
      <template #actions>
        <button v-if="commandHistory.length" class="btn flat sm" @click="commandHistory.splice(0)">
          <Icon :path="mdiTrashCanOutline" :size="16" />{{ t("clearHistory") }}
        </button>
      </template>
      <Empty v-if="!commandHistory.length" :icon="mdiHistory" :text="t('noHistory')" />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>{{ t("time") }}</th>
              <th>{{ t("lineShort") }}</th>
              <th>Frames</th>
              <th>{{ t("description") }}</th>
              <th>{{ t("answers") }}</th>
              <th class="right">ms</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in commandHistory" :key="h.id">
              <td class="mono small nowrap">{{ fmtMs(h.ts) }}</td>
              <td>{{ h.line }}</td>
              <td class="mono small">{{ h.frames.map(bytesHex).join(", ") }}</td>
              <td class="small">{{ h.text }}</td>
              <td class="small">
                <span v-if="h.error" class="chip err" :title="h.error">{{ t("error") }}</span>
                <span v-else-if="!h.answers.length" class="faint">–</span>
                <span v-else class="mono">{{ h.answers.map((v) => (v < 0 ? "–" : v)).join(", ") }}</span>
                <div v-if="histExplain(h)" class="faint small">{{ histExplain(h) }}</div>
              </td>
              <td class="right mono small">{{ h.ms }}</td>
              <td class="nowrap right">
                <button class="btn icon sm" :title="t('loadEntry')" @click="loadEntry(h)"><Icon :path="mdiPencil" :size="16" /></button>
                <button class="btn icon sm" :title="t('resend')" :disabled="sending" @click="resend(h)"><Icon :path="mdiReplay" :size="16" /></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <details class="card cheat mt">
      <summary>{{ t("cheat") }}</summary>
      <div class="cheat-body">
        <table class="table small">
          <thead>
            <tr><th>{{ t("addrByte") }}</th><th>{{ t("meaning") }}</th></tr>
          </thead>
          <tbody>
            <tr><td class="mono">0AAA AAAS</td><td>{{ t("c_short") }}</td></tr>
            <tr><td class="mono">100G GGGS</td><td>{{ t("c_group") }}</td></tr>
            <tr><td class="mono">1111 111S</td><td>{{ t("c_bc") }}</td></tr>
            <tr><td class="mono">1111 110S</td><td>{{ t("c_bcu") }}</td></tr>
            <tr><td class="mono">101C CCC1 / 110C CCC1</td><td>{{ t("c_special") }}</td></tr>
            <tr><td class="mono">S = 0 / 1</td><td>{{ t("c_s") }}</td></tr>
          </tbody>
        </table>
        <p class="small muted">{{ t("c_note") }}</p>
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  mdiAlertCircle,
  mdiAlertOutline,
  mdiConsoleLine,
  mdiHistory,
  mdiInformationOutline,
  mdiLightbulbOnOutline,
  mdiPencil,
  mdiReplay,
  mdiReply,
  mdiSend,
  mdiTrashCanOutline,
} from "@mdi/js";
import Card from "../Card.vue";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import { gw } from "../../lib/api";
import { confirmDialog, gatewayOnline, state } from "../../lib/store";
import { lang, useT } from "../../lib/i18n";
import {
  DEVICE_COMMANDS,
  GEAR_COMMANDS,
  SPECIAL_COMMANDS_16,
  bin8,
  bytesHex,
  commandDraft,
  commandHistory,
  describeFrames,
  explainAnswer,
  fmtMs,
  hex2,
  kindLabel,
  kindStyle,
  levelPct,
  parseHexFrames,
  type CommandHistoryEntry,
  type Described,
} from "./frames";

const t = useT({
  de: {
    warnTitle: "Expertenfunktion:",
    warnText: "Hier werden DALI-Frames direkt auf den Bus gesendet – ohne Plausibilitätsprüfung durch das Gateway. Konfigurationsbefehle (z. B. RESET, SET SHORT ADDRESS, ADD TO GROUP) verändern Geräte dauerhaft.",
    compose: "Frame zusammenstellen",
    composeSub: "IEC 62386-102 / -103",
    m16Hint: "16-Bit-Frames steuern Betriebsgeräte (Leuchten, IEC 62386-102).",
    m24Hint: "24-Bit-Frames adressieren Steuergeräte wie Taster und Sensoren (IEC 62386-103).",
    raw: "Roh-Hex",
    rawHint: "Beliebige Frames als Hex-Bytes eingeben.",
    addressing: "Adressierung",
    shortAddr: "Kurzadresse",
    pickDevice: "Gerät auswählen",
    at_short: "Kurzadresse",
    at_group: "Gruppe",
    at_group24: "Gerätegruppe",
    at_bc: "Broadcast",
    at_bcu: "Unadressierte",
    at_special: "Spezialbefehl",
    specialCmd: "Spezialbefehl",
    dataByte: "Datenbyte",
    selector: "Selektor-Bit S",
    selCmd: "Befehl (S = 1)",
    selDapc: "DAPC – Dimmwert (S = 0)",
    level: "Dimmwert (0–254)",
    command: "Befehl",
    customOpcode: "Eigener Opcode…",
    sceneN: "Szene n",
    groupN: "Gruppe n",
    deviceGroup: "Gerätegruppe",
    instance: "Instanz",
    instDevice: "Gerät",
    instNumber: "Instanznummer",
    instType: "Instanztyp",
    instAll: "Alle Instanzen",
    cat_control: "Steuerung",
    cat_query: "Abfragen",
    cat_config: "Konfiguration (2× senden)",
    rawLabel: "Frames (Hex)",
    rawPh: "z. B. FF 05   oder   C1 06, 0B F0",
    rawHint2: "2 Bytes = 16-Bit-Frame, 3 Bytes = 24-Bit-Frame. Mehrere Frames mit Komma oder Zeilenumbruch trennen (gleiche Länge).",
    rawErr_odd: "Ungerade Anzahl Hex-Zeichen.",
    rawErr_len: "Jeder Frame muss 2 (16 Bit) oder 3 Bytes (24 Bit) lang sein.",
    rawErr_mixed: "16- und 24-Bit-Frames können nicht gemischt werden.",
    rawErr_empty: "Bitte mindestens einen Frame eingeben.",
    setDtr0: "Vorher DTR0 setzen auf",
    sendTwice: "2× senden (Konfigurationsbefehle werden nur bei doppeltem Empfang innerhalb 100 ms ausgeführt)",
    dtrShort: "Für SET SHORT ADDRESS: DTR0 = (Adresse × 2) + 1, oder 255 zum Löschen der Adresse.",
    dtrLevel: "DTR0 = Dimmwert 0–254 (255 = MASK).",
    dtrFade: "DTR0 = Code 0–15.",
    quick: "Schnellabfragen (sofort senden)",
    preview: "Vorschau",
    lv_aux: "Hilfsbefehl",
    lv_aux_h: "Setzt nur Register oder Kontext (DTR, Gerätetyp) – verändert keine Einstellungen.",
    lv_query: "Abfrage",
    lv_query_h: "Liest nur Werte, verändert nichts.",
    lv_control: "Steuerbefehl",
    lv_control_h: "Schaltet/dimmt – jederzeit umkehrbar.",
    lv_config: "Konfiguration",
    lv_config_h: "Ändert gespeicherte Geräteeinstellungen.",
    lv_danger: "Kritisch",
    lv_danger_h: "Kann Adressen oder die gesamte Konfiguration verändern.",
    send: "Senden",
    result: "Antwort",
    noResult: "Noch nichts gesendet.",
    sent: "Gesendet",
    answers: "Antwort",
    noAnswerQuery: "Keine Antwort – bei JA/NEIN-Abfragen bedeutet das „NEIN“, sonst ist das Gerät nicht erreichbar.",
    noAnswerCmd: "Befehle werden nicht beantwortet.",
    noAnswerCode: "keine Antwort ({v})",
    history: "Verlauf",
    historySub: "Gesendete Frames dieser Sitzung",
    clearHistory: "Verlauf leeren",
    noHistory: "Noch keine Befehle gesendet.",
    lineShort: "L",
    description: "Beschreibung",
    loadEntry: "In den Editor laden",
    resend: "Erneut senden",
    confirmCfgTitle: "Konfigurationsbefehl senden?",
    confirmDangerTitle: "Kritischen Befehl senden?",
    confirmMsg: "Folgende Frames werden auf Linie {line} gesendet:\n\n{frames}",
    confirmDangerMsg: "\n\nDieser Befehl kann Adressen oder gespeicherte Einstellungen dauerhaft verändern.",
    confirmSend: "Senden",
    cheat: "Kurzreferenz: Adressbyte (16 Bit)",
    addrByte: "Adressbyte",
    meaning: "Bedeutung",
    c_short: "Kurzadresse A = 0–63",
    c_group: "Gruppenadresse G = 0–15",
    c_bc: "Broadcast an alle Betriebsgeräte",
    c_bcu: "Broadcast an alle Geräte ohne Kurzadresse",
    c_special: "Spezialbefehle (DTR0 = 0xA3, INITIALISE = 0xA5, ENABLE DEVICE TYPE = 0xC1 …)",
    c_s: "0 = zweites Byte ist ein Dimmwert (DAPC), 1 = zweites Byte ist ein Befehl",
    c_note: "Gerätetyp-spezifische Befehle (224–255) benötigen direkt davor ENABLE DEVICE TYPE (C1 xx) – im Roh-Modus als zwei Frames senden, z. B. „C1 06, 01 F1“.",
  },
  en: {
    warnTitle: "Expert feature:",
    warnText: "DALI frames are sent directly to the bus – without plausibility checks by the gateway. Configuration commands (e.g. RESET, SET SHORT ADDRESS, ADD TO GROUP) change devices permanently.",
    compose: "Compose frame",
    composeSub: "IEC 62386-102 / -103",
    m16Hint: "16 bit frames control control gear (luminaires, IEC 62386-102).",
    m24Hint: "24 bit frames address control devices such as push buttons and sensors (IEC 62386-103).",
    raw: "Raw hex",
    rawHint: "Enter arbitrary frames as hex bytes.",
    addressing: "Addressing",
    shortAddr: "Short address",
    pickDevice: "Pick device",
    at_short: "Short address",
    at_group: "Group",
    at_group24: "Device group",
    at_bc: "Broadcast",
    at_bcu: "Unaddressed",
    at_special: "Special command",
    specialCmd: "Special command",
    dataByte: "Data byte",
    selector: "Selector bit S",
    selCmd: "Command (S = 1)",
    selDapc: "DAPC – level (S = 0)",
    level: "Level (0–254)",
    command: "Command",
    customOpcode: "Custom opcode…",
    sceneN: "Scene n",
    groupN: "Group n",
    deviceGroup: "Device group",
    instance: "Instance",
    instDevice: "Device",
    instNumber: "Instance number",
    instType: "Instance type",
    instAll: "All instances",
    cat_control: "Control",
    cat_query: "Queries",
    cat_config: "Configuration (send twice)",
    rawLabel: "Frames (hex)",
    rawPh: "e.g. FF 05   or   C1 06, 0B F0",
    rawHint2: "2 bytes = 16 bit frame, 3 bytes = 24 bit frame. Separate several frames with commas or new lines (same length).",
    rawErr_odd: "Odd number of hex digits.",
    rawErr_len: "Every frame must be 2 (16 bit) or 3 bytes (24 bit) long.",
    rawErr_mixed: "16 and 24 bit frames cannot be mixed.",
    rawErr_empty: "Please enter at least one frame.",
    setDtr0: "Set DTR0 first to",
    sendTwice: "Send twice (configuration commands are only executed when received twice within 100 ms)",
    dtrShort: "For SET SHORT ADDRESS: DTR0 = (address × 2) + 1, or 255 to delete the address.",
    dtrLevel: "DTR0 = level 0–254 (255 = MASK).",
    dtrFade: "DTR0 = code 0–15.",
    quick: "Quick queries (sent immediately)",
    preview: "Preview",
    lv_aux: "Auxiliary command",
    lv_aux_h: "Only sets registers or context (DTR, device type) – changes no settings.",
    lv_query: "Query",
    lv_query_h: "Only reads values, changes nothing.",
    lv_control: "Control command",
    lv_control_h: "Switches/dims – reversible at any time.",
    lv_config: "Configuration",
    lv_config_h: "Changes stored device settings.",
    lv_danger: "Critical",
    lv_danger_h: "May change addresses or the whole configuration.",
    send: "Send",
    result: "Answer",
    noResult: "Nothing sent yet.",
    sent: "Sent",
    answers: "Answer",
    noAnswerQuery: "No answer – for yes/no queries this means “NO”, otherwise the device is not reachable.",
    noAnswerCmd: "Commands are not answered.",
    noAnswerCode: "no answer ({v})",
    history: "History",
    historySub: "Frames sent in this session",
    clearHistory: "Clear history",
    noHistory: "No commands sent yet.",
    lineShort: "L",
    description: "Description",
    loadEntry: "Load into editor",
    resend: "Send again",
    confirmCfgTitle: "Send configuration command?",
    confirmDangerTitle: "Send critical command?",
    confirmMsg: "The following frames will be sent on line {line}:\n\n{frames}",
    confirmDangerMsg: "\n\nThis command may permanently change addresses or stored settings.",
    confirmSend: "Send",
    cheat: "Quick reference: address byte (16 bit)",
    addrByte: "Address byte",
    meaning: "Meaning",
    c_short: "Short address A = 0–63",
    c_group: "Group address G = 0–15",
    c_bc: "Broadcast to all control gear",
    c_bcu: "Broadcast to all devices without short address",
    c_special: "Special commands (DTR0 = 0xA3, INITIALISE = 0xA5, ENABLE DEVICE TYPE = 0xC1 …)",
    c_s: "0 = second byte is a level (DAPC), 1 = second byte is a command",
    c_note: "Device type specific commands (224–255) require ENABLE DEVICE TYPE (C1 xx) right before – send both frames in raw mode, e.g. “C1 06, 01 F1”.",
  },
});

const online = computed(() => gatewayOnline());
const lineIds = computed(() => {
  const n = Number(state.info?.descriptor?.lines) || Object.keys(state.info?.lines || {}).length || 1;
  return Array.from({ length: n }, (_, i) => i);
});

// ------------------------------------------------------------ pick lists
interface Pick {
  op: number;
  cat: "control" | "query" | "config";
  param?: "scene" | "group";
}
const GEAR_PICK: Pick[] = [
  ...[0, 5, 6, 1, 2, 3, 4, 7, 8, 10].map((op) => ({ op, cat: "control" as const })),
  { op: 16, cat: "control", param: "scene" },
  ...[144, 160, 161, 162, 154, 163, 164, 165, 168, 153, 167, 151, 159, 158, 145, 146, 147, 148, 149, 150, 155, 170, 152, 156, 157].map((op) => ({ op, cat: "query" as const })),
  { op: 176, cat: "query", param: "scene" },
  ...[192, 193, 194, 195, 196].map((op) => ({ op, cat: "query" as const })),
  ...[37, 34, 33, 42, 43, 44, 45, 46, 47, 48].map((op) => ({ op, cat: "config" as const })),
  { op: 64, cat: "config", param: "scene" },
  { op: 80, cat: "config", param: "scene" },
  { op: 96, cat: "config", param: "group" },
  { op: 112, cat: "config", param: "group" },
  ...[128, 32].map((op) => ({ op, cat: "config" as const })),
];
const DEVICE_PICK: Pick[] = [
  ...[0x30, 0x35, 0x34, 0x33, 0x31, 0x32, 0x46, 0x3e, 0x40, 0x48, 0x41, 0x42, 0x43, 0x44, 0x45, 0x3d, 0x80, 0x81, 0x82, 0x83, 0x86, 0x88, 0x8b, 0x8c, 0x8d, 0x8e].map((op) => ({
    op,
    cat: "query" as const,
  })),
  ...[0x00, 0x01, 0x1d, 0x1e, 0x61, 0x62, 0x1f, 0x20, 0x16, 0x17, 0x21, 0x66, 0x68, 0x63, 0x64, 0x65, 0x14, 0x10].map((op) => ({ op, cat: "config" as const })),
];
const SPECIAL_PICK = [0xa1, 0xa3, 0xc3, 0xc5, 0xc1, 0xad, 0xbb, 0xb9, 0xa9, 0xab, 0xb1, 0xb3, 0xb5, 0xb7, 0xa5, 0xa7];
const QUICK = [144, 160, 153, 192, 193, 161, 162, 165, 154];

function grouped(list: Pick[]) {
  return (["control", "query", "config"] as const)
    .map((cat) => ({ cat, label: t(`cat_${cat}`), items: list.filter((p) => p.cat === cat) }))
    .filter((g) => g.items.length);
}
const groups16 = computed(() => grouped(GEAR_PICK));
const groups24 = computed(() => grouped(DEVICE_PICK));
function pickLabel16(p: Pick) {
  const name = GEAR_COMMANDS[p.op] || `COMMAND ${p.op}`;
  return p.param ? `${name.replace(/ 0( |$)/, " n$1")}  (${p.op}+n)` : `${name}  (${p.op})`;
}

// ------------------------------------------------------------ builder state
type Mode = "16" | "24" | "raw";
const mode = ref<Mode>("16");
const line = ref(0);
const clamp = (v: any, lo: number, hi: number) => Math.max(lo, Math.min(hi, Math.round(Number(v) || 0)));

type At16 = "short" | "group" | "broadcast" | "unaddr" | "special";
const at16 = ref<At16>("short");
const at16Opts = computed(() => [
  { id: "short" as At16, label: t("at_short") },
  { id: "group" as At16, label: t("at_group") },
  { id: "broadcast" as At16, label: t("at_bc") },
  { id: "unaddr" as At16, label: t("at_bcu") },
  { id: "special" as At16, label: t("at_special") },
]);
const shortAddr = ref(0);
const groupAddr = ref(0);
const sel16 = ref<"cmd" | "dapc">("cmd");
const dapcLevel = ref(254);
const cmd16 = ref("144");
const param16 = ref(0);
const custom16 = ref(0);
const special = ref(0xa3);
const specialData = ref(0);

type At24 = "short" | "group" | "broadcast" | "unaddr";
const at24 = ref<At24>("short");
const at24Opts = computed(() => [
  { id: "short" as At24, label: t("at_short") },
  { id: "group" as At24, label: t("at_group24") },
  { id: "broadcast" as At24, label: t("at_bc") },
  { id: "unaddr" as At24, label: t("at_bcu") },
]);
const short24 = ref(0);
const group24 = ref(0);
const inst = ref<"device" | "number" | "type" | "all">("device");
const instNum = ref(0);
const cmd24 = ref(String(0x30));
const custom24 = ref(0);

const rawText = ref("");
const useDtr0 = ref(true);
const dtr0 = ref(0);
const sendTwice = ref(false);

const lineDevices = computed(() => Object.values(state.devices).filter((d) => (d.line ?? 0) === line.value).sort((a, b) => a.address - b.address));
const deviceAtAddr = computed(() => lineDevices.value.find((d) => d.address === clamp(shortAddr.value, 0, 63)));
function pickDevice(id: string) {
  const d = state.devices[Number(id)];
  if (d) shortAddr.value = d.address;
}

const pick16 = computed(() => GEAR_PICK.find((p) => String(p.op) === cmd16.value));
const opcode16 = computed(() => (cmd16.value === "custom" ? clamp(custom16.value, 0, 255) : pick16.value ? pick16.value.op + (pick16.value.param ? clamp(param16.value, 0, 15) : 0) : 0));
const addrByte16 = computed(() => {
  const S = sel16.value === "cmd" ? 1 : 0;
  switch (at16.value) {
    case "short":
      return (clamp(shortAddr.value, 0, 63) << 1) | S;
    case "group":
      return 0x80 | (clamp(groupAddr.value, 0, 15) << 1) | S;
    case "broadcast":
      return 0xfe | S;
    case "unaddr":
      return 0xfc | S;
    default:
      return special.value;
  }
});
const second16 = computed(() => (at16.value === "special" ? clamp(specialData.value, 0, 255) : sel16.value === "dapc" ? clamp(dapcLevel.value, 0, 255) : opcode16.value));

const opcode24 = computed(() => (cmd24.value === "custom" ? clamp(custom24.value, 0, 255) : Number(cmd24.value)));
const addrByte24 = computed(() => {
  switch (at24.value) {
    case "short":
      return (clamp(short24.value, 0, 63) << 1) | 1;
    case "group":
      return 0x80 | (clamp(group24.value, 0, 31) << 1) | 1;
    case "broadcast":
      return 0xff;
    default:
      return 0xfd;
  }
});
const instByte = computed(() => {
  switch (inst.value) {
    case "device":
      return 0xfe;
    case "all":
      return 0xff;
    case "number":
      return clamp(instNum.value, 0, 31);
    default:
      return 0x80 | clamp(instNum.value, 0, 31);
  }
});
// instance commands (0x60…0x9F) address an instance, the others the device
watch(cmd24, (c) => {
  const op = Number(c);
  if (!Number.isNaN(op)) inst.value = op >= 0x60 && op <= 0x9f ? (inst.value === "device" ? "number" : inst.value) : "device";
});

const mainName = computed(() => {
  if (mode.value === "16") return at16.value === "special" ? SPECIAL_COMMANDS_16[special.value] || "" : sel16.value === "dapc" ? "DAPC" : GEAR_COMMANDS[opcode16.value] || "";
  if (mode.value === "24") return DEVICE_COMMANDS[opcode24.value] || "";
  return "";
});
const needsDtr = computed(() => mode.value !== "raw" && mainName.value.includes("(DTR0)"));
const dtrHint = computed(() => {
  const n = mainName.value;
  if (n.startsWith("SET SHORT ADDRESS")) return t("dtrShort");
  if (/LEVEL|SCENE/.test(n)) return t("dtrLevel");
  if (/FADE/.test(n)) return t("dtrFade");
  return "";
});
const isConfigSel = computed(() => {
  if (mode.value === "16") {
    if (at16.value === "special") return [0xa5, 0xa7].includes(special.value);
    return sel16.value === "cmd" && opcode16.value >= 32 && opcode16.value <= 129;
  }
  if (mode.value === "24") return opcode24.value < 0x30 || (opcode24.value >= 0x60 && opcode24.value < 0x80);
  return false;
});
watch(isConfigSel, (v) => (sendTwice.value = v), { immediate: true });

const built = computed<{ bits: 16 | 24; frames: number[][]; error?: string }>(() => {
  if (mode.value === "raw") {
    const r = parseHexFrames(rawText.value);
    if (r.error) return { bits: 16, frames: [], error: t(`rawErr_${r.error}`) };
    return { bits: r.frames[0].length === 3 ? 24 : 16, frames: r.frames };
  }
  const out: number[][] = [];
  if (mode.value === "16") {
    const main = [addrByte16.value, second16.value];
    if (needsDtr.value && useDtr0.value) out.push([0xa3, clamp(dtr0.value, 0, 255)]);
    out.push(main);
    if (isConfigSel.value && sendTwice.value) out.push([...main]);
    return { bits: 16, frames: out };
  }
  const main = [addrByte24.value, instByte.value, opcode24.value];
  if (needsDtr.value && useDtr0.value) out.push([0xc1, 0x30, clamp(dtr0.value, 0, 255)]);
  out.push(main);
  if (isConfigSel.value && sendTwice.value) out.push([...main]);
  return { bits: 24, frames: out };
});

// ------------------------------------------------------------ classification
type Level = "aux" | "query" | "control" | "config" | "danger";
const ORDER: Level[] = ["aux", "query", "control", "config", "danger"];
function classify(b: number[], d: Described): Level {
  if (b.length === 2) {
    const [a, c] = b;
    if (d.kind === "special") return [0xa5, 0xa7, 0xb7, 0xc7, 0xc9].includes(a) ? "danger" : d.query ? "query" : "aux";
    if (d.kind === "dapc") return "control";
    if (d.query) return "query";
    if (c >= 224) return /^(SET TEMPORARY|ACTIVATE|[XY]-COORDINATE STEP|COLOUR TEMPERATURE STEP|COPY REPORT)/.test(d.name) ? "control" : "config";
    if ([32, 35, 36, 128, 129].includes(c)) return "danger";
    if (c >= 32 && c <= 129) return a >= 0x80 ? "danger" : "config";
    return "control";
  }
  const [a, i, c] = b;
  if (!(a & 1)) return "control"; // event frame (emulates an input device)
  if (a === 0xc1) return [0x01, 0x02, 0x08, 0x20, 0x21].includes(i) ? "danger" : [0x03, 0x09, 0x0a].includes(i) ? "query" : "aux";
  if (d.query) return "query";
  if ([0x10, 0x11, 0x14, 0x15, 0x18].includes(c)) return "danger";
  if (c < 0x30 || (c >= 0x60 && c < 0x80)) return a & 0x80 ? "danger" : "config";
  return "control";
}
function classifyAll(frames: number[][]): Level {
  const desc = describeFrames(frames);
  return frames.reduce<Level>((acc, f, i) => {
    const l = classify(f, desc[i]);
    return ORDER.indexOf(l) > ORDER.indexOf(acc) ? l : acc;
  }, "aux");
}
const builtDesc = computed(() => describeFrames(built.value.frames));
const sendLevel = computed<Level>(() => classifyAll(built.value.frames));
const levelMeta = computed(() => {
  const l = sendLevel.value;
  const chip = { aux: "", query: "primary", control: "ok", config: "warn", danger: "err" }[l];
  return { chip, label: t(`lv_${l}`), hint: t(`lv_${l}_h`) };
});

// ------------------------------------------------------------ sending
const sending = ref(false);
let seq = 0;
const last = computed<CommandHistoryEntry | null>(() => commandHistory[0] ?? null);
const lastDesc = computed(() => (last.value ? describeFrames(last.value.frames) : []));
const validByte = (v: any) => typeof v === "number" && v >= 0 && v <= 255;

function normalizeAnswers(res: any): number[] {
  if (Array.isArray(res)) return res.map((v) => (v === null ? -1 : Number(v)));
  if (typeof res === "number") return [res];
  return [];
}

async function sendFrames(bits: 16 | 24, lineNo: number, frames: number[][], ask = true) {
  if (!frames.length) return;
  const level = classifyAll(frames);
  const desc = describeFrames(frames);
  if (ask && (level === "config" || level === "danger")) {
    const list = frames.map((f, i) => `${bytesHex(f)}  –  ${desc[i].text}`).join("\n");
    const ok = await confirmDialog({
      title: level === "danger" ? t("confirmDangerTitle") : t("confirmCfgTitle"),
      message: t("confirmMsg", { line: lineNo, frames: list }) + (level === "danger" ? t("confirmDangerMsg") : ""),
      danger: level === "danger",
      confirmText: t("confirmSend"),
    });
    if (!ok) return;
  }
  const lastQuery = [...desc].reverse().find((d) => d.query);
  const entry: CommandHistoryEntry = {
    id: ++seq + Date.now(),
    ts: Date.now() / 1000,
    line: lineNo,
    bits,
    frames: frames.map((f) => [...f]),
    text: desc.map((d) => d.text).join(" → "),
    answers: [],
    ms: 0,
    query: !!lastQuery,
    queryName: lastQuery?.text,
  };
  sending.value = true;
  const t0 = performance.now();
  try {
    const body =
      bits === 16 ? frames.map(([a, c]) => ({ address: a, command: c })) : frames.map(([a, i, c]) => ({ address: a, instance: i, command: c }));
    const res = await gw.post(`/dali/sendDali${bits}/${lineNo}`, body);
    entry.answers = normalizeAnswers(res);
  } catch (e: any) {
    entry.error = e?.message || String(e);
  } finally {
    entry.ms = Math.round(performance.now() - t0);
    sending.value = false;
  }
  commandHistory.unshift(entry);
  if (commandHistory.length > 200) commandHistory.length = 200;
}

function sendBuilt() {
  const b = built.value;
  if (b.error) return;
  return sendFrames(b.bits, line.value, b.frames);
}

function quickQuery(op: number) {
  mode.value = "16";
  sel16.value = "cmd";
  const p = GEAR_PICK.find((x) => x.op === op);
  if (p) cmd16.value = String(op);
  const a = addrByte16.value | 1;
  return sendFrames(16, line.value, [[a, op]], false);
}

function loadEntry(h: CommandHistoryEntry) {
  mode.value = "raw";
  line.value = h.line;
  rawText.value = h.frames.map(bytesHex).join(", ");
}
function resend(h: CommandHistoryEntry) {
  return sendFrames(h.bits, h.line, h.frames);
}

function lastAnswerFor(h: CommandHistoryEntry): number | null {
  const vals = h.answers.filter(validByte);
  return vals.length ? vals[vals.length - 1] : null;
}
const lastExplain = computed(() => {
  const h = last.value;
  if (!h || !h.query || h.error) return null;
  const v = lastAnswerFor(h);
  return v === null ? null : explainAnswer(h.queryName, v, lang.value);
});
function histExplain(h: CommandHistoryEntry) {
  if (!h.query || h.error) return "";
  const v = lastAnswerFor(h);
  return v === null ? "" : explainAnswer(h.queryName, v, lang.value)?.summary ?? "";
}
function shortName(n?: string) {
  if (!n) return "";
  const i = n.lastIndexOf(": ");
  return i >= 0 ? n.slice(i + 2) : n;
}

// frames handed over from the monitor
watch(
  commandDraft,
  (d) => {
    if (!d) return;
    mode.value = "raw";
    line.value = d.line;
    rawText.value = d.frames.map(bytesHex).join(", ");
    commandDraft.value = null;
  },
  { immediate: true },
);
</script>

<style scoped>
.cmd-grid { grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); align-items: start; }
.line-field { width: 140px; }
.wrap-group { flex-wrap: wrap; border-radius: 14px; }
.cmd-field { grid-column: 1 / -1; }
.num { width: 84px; flex: 0 0 auto; }
.opts { display: flex; flex-direction: column; gap: 8px; padding: 10px 12px; background: var(--bg2); border-radius: 10px; }
.check { display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer; flex-wrap: wrap; }
.check .num { height: 32px; background: var(--card); }
.quick { gap: 6px; }
.quick .chip { border: 0; font-family: inherit; }
.quick .chip:disabled { opacity: .5; cursor: wait; }
.preview { display: flex; flex-direction: column; gap: 6px; }
.pv-row { display: grid; grid-template-columns: auto auto 1fr; grid-template-areas: "kind hex bin" "text text text"; gap: 2px 10px; align-items: center; padding: 8px 10px; background: var(--bg2); border-radius: 10px; }
.pv-row .kbadge { grid-area: kind; }
.pv-hex { grid-area: hex; font-size: 15px; font-weight: 600; }
.pv-bin { grid-area: bin; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pv-text { grid-area: text; color: var(--text2); }
.kbadge { display: inline-flex; align-items: center; height: 22px; padding: 0 8px; border-radius: 11px; font-size: 11.5px; font-weight: 600; }
.mt-s { margin-top: 6px; }
.answers { display: flex; flex-wrap: wrap; gap: 10px; }
.ans { background: var(--bg2); border-radius: 12px; padding: 10px 16px; min-width: 110px; }
.ans-big { font-size: 26px; font-weight: 500; line-height: 1.1; }
.status-bits { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 4px 14px; }
.sbit { display: flex; align-items: center; gap: 8px; color: var(--text3); }
.sbit.on { color: var(--text); font-weight: 500; }
.sbit.err { color: var(--error); }
.bitno { width: 12px; }
.spinner.mini { width: 14px; height: 14px; }
.spinner.light { border-color: rgba(255,255,255,.35); border-top-color: #fff; }
.cheat { padding: 0; }
.cheat summary { padding: 14px 16px; cursor: pointer; font-weight: 500; }
.cheat-body { padding: 0 16px 14px; }
@media (max-width: 700px) {
  .cmd-grid { grid-template-columns: 1fr; }
  .line-field { width: 120px; }
  .pv-row { grid-template-columns: auto 1fr; grid-template-areas: "kind hex" "bin bin" "text text"; }
}
</style>
