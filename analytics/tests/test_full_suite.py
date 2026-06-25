import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from collections import defaultdict, Counter

GREEN = "\033[92m"; RED = "\033[91m"; BLUE = "\033[94m"
RESET = "\033[0m";  BOLD = "\033[1m"

passed = 0; failed = 0; errors = []

def ok(name):
    global passed; passed += 1
    print(f"  {GREEN}PASS{RESET}  {name}")

def fail(name, reason):
    global failed; failed += 1; errors.append((name, reason))
    print(f"  {RED}FAIL{RESET}  {name}")
    print(f"         {RED}→ {reason}{RESET}")

def section(title):
    print(f"\n{BOLD}{BLUE}{'─'*55}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'─'*55}{RESET}")

# ── SECTION 1: STATE EXTRACTOR ──────────────────────────────────────────────
section("1 / 7   State Extractor")
try:
    from analytics.state_extraction.state_extractor import StateExtractor
    se = StateExtractor()

    def make_session(sid, ctmc_state, activity="session", action="Login",
                     level=3.0, after_hours=0):
        return {"session_id": sid, "user_id": "u1", "events": [{
            "event_id":"E1","user_id":"u1","timestamp":"2026-06-25T09:00:00Z",
            "Activity":activity,"Action":action,"Level":level,"Command":"",
            "file_path":"","bytes":0,"IsAfterHours":after_hours,"IsWeekend":0,
            "CTMC_State":ctmc_state,"Anomaly":0}]}

    s = se.extract_states(make_session("T1","Login"))
    ok("Normal login → Login state") if s==["Login"] else fail("Normal login","Got "+str(s))

    s = se.extract_states(make_session("T2","Login",after_hours=1))
    ok("Pre-computed state used directly") if s==["Login"] else fail("Pre-computed state","Got "+str(s))

    s = se.extract_states(make_session("T3","",activity="command",
                                       action="Command executed",level=10.0))
    ok(f"Derives state when CTMC_State empty → {s[0] if s else 'none'}") if s else fail("Derives state","Empty")

    s = se.extract_states({"session_id":"T4","user_id":"u1","events":[]})
    ok("Empty session returns []") if s==[] else fail("Empty session","Got "+str(s))

    multi = {"session_id":"T5","user_id":"u1","events":[
        {"event_id":"E1","user_id":"u1","timestamp":"2026-06-25T09:00:00Z",
         "Activity":"s","Action":"l","Level":3,"Command":"","file_path":"",
         "bytes":0,"IsAfterHours":0,"IsWeekend":0,"CTMC_State":st,"Anomaly":0}
        for st in ["Login","File_Access","Email"]]}
    s = se.extract_states(multi)
    ok("Multi-event order preserved") if s==["Login","File_Access","Email"] else fail("Order preserved","Got "+str(s))

except Exception as e:
    fail("State Extractor", str(e))

# ── SECTION 2: CTMC SCORER ──────────────────────────────────────────────────
section("2 / 7   CTMC Scorer")
try:
    from analytics.ctmc.ctmc_scorer import CTMCScorer
    ctmc = CTMCScorer()
    mx = {"Login":{"File_Access":0.99}}

    s = ctmc.score(["Login","File_Access"], mx, 20)
    ok(f"Likely transition scores low → {s:.1f}") if s<=20 else fail("Likely low",f"Got {s:.1f}")

    s = ctmc.score(["Login","File_Delete"], {}, 20)
    ok(f"Unseen transition scores high → {s:.1f}") if s>=50 else fail("Unseen high",f"Got {s:.1f}")

    s = ctmc.score(["Login"], mx, 20)
    ok("Single state → 0.0") if s==0.0 else fail("Single state",f"Got {s}")

    s = ctmc.score([], mx, 20)
    ok("Empty sequence → 0.0") if s==0.0 else fail("Empty sequence",f"Got {s}")

    import random; random.seed(42)
    vocab = ["Login","File_Access","Email","Command","Logout"]
    bad = False
    for _ in range(50):
        seq = [random.choice(vocab) for _ in range(random.randint(2,10))]
        sc  = ctmc.score(seq, {}, random.randint(0,30))
        if not (0<=sc<=100): bad=True; fail("Always 0-100",f"Got {sc}"); break
    if not bad: ok("Score always in [0,100] — 50 random tests")

    s_new = ctmc.score(["Login","File_Delete"],{},0)
    s_exp = ctmc.score(["Login","File_Delete"],{},20)
    ok(f"Trust dampening: new({s_new:.1f}) ≤ exp({s_exp:.1f})") if s_new<=s_exp else fail("Dampening","New > exp")

    s_risky  = ctmc.score(["Login","Suspicious_Command"],{},20)
    s_normal = ctmc.score(["Login","File_Access"],mx,20)
    ok(f"High-risk bonus: Suspicious({s_risky:.1f}) > normal({s_normal:.1f})") if s_risky>s_normal else fail("Risk bonus",f"{s_risky} not > {s_normal}")

except Exception as e:
    fail("CTMC Scorer", str(e))

# ── SECTION 3: RULE ENGINE ──────────────────────────────────────────────────
section("3 / 7   Rule Engine")
try:
    from analytics.rule_engine.rule_engine import RuleEngine
    re = RuleEngine()

    def ev(ctmc_state, after_hours=0, level=3.0):
        return {"event_id":"E1","user_id":"u1","timestamp":"2026-06-25T09:00:00Z",
                "Activity":"session","Action":"Login","Level":level,"Command":"",
                "file_path":"","bytes":0,"IsAfterHours":after_hours,
                "IsWeekend":0,"CTMC_State":ctmc_state,"Anomaly":0}

    def ids(violations): return [v.rule_id for v in violations]

    v=re.check_all_rules([],[],   "u"); ok("Empty → no violations") if v==[] else fail("Empty",str(ids(v)))
    v=re.check_all_rules(["Login"],[ev("Login",1)],"u"); ok("R01 fires after-hours") if "R01" in ids(v) else fail("R01",str(ids(v)))
    v=re.check_all_rules(["Login"],[ev("Login",0)],"u"); ok("R01 not work hours") if "R01" not in ids(v) else fail("R01 work hours","Fired")
    v=re.check_all_rules(["Login_Failed"]*3+["Login"],[],  "u"); ok("R04 fires 3+ failures") if "R04" in ids(v) else fail("R04",str(ids(v)))
    v=re.check_all_rules(["Login_Failed"]*2+["Login"],[],  "u"); ok("R04 not 2 failures") if "R04" not in ids(v) else fail("R04 2 fail","Fired")
    v=re.check_all_rules(["Login","File_Access","File_Add"],[],  "u"); ok("R30 file then upload") if "R30" in ids(v) else fail("R30",str(ids(v)))
    v=re.check_all_rules(["Login_Failed","Login_Failed","Login"],[],  "u"); ok("R28 fail then success") if "R28" in ids(v) else fail("R28",str(ids(v)))
    v=re.check_all_rules(["Login","Login_Failed","Login_Failed"],[],  "u"); ok("R28 not success first") if "R28" not in ids(v) else fail("R28 order","Fired")
    v=re.check_all_rules(["Command"],[ev("Command",level=12.0)],  "u"); ok("R35 high level") if "R35" in ids(v) else fail("R35",str(ids(v)))
    v=re.check_all_rules(["Command"],[ev("Command",level=3.0)],   "u"); ok("R35 not low level") if "R35" not in ids(v) else fail("R35 low","Fired")
    v=re.check_all_rules(["Login"]*8,[],  "u"); ok("R37 login-only session") if "R37" in ids(v) else fail("R37",str(ids(v)))
    v=re.check_all_rules(["Login"]*8+["File_Access"],[],  "u"); ok("R37 not mixed states") if "R37" not in ids(v) else fail("R37 mixed","Fired")

    states13=["Login_Failed"]*3+["Login","File_Access","File_Add","Email"]
    events13=[ev("Login",after_hours=1,level=11.0)]
    v13=re.check_all_rules(states13,events13,"u")
    ok(f"All contributions positive ({len(v13)} rules, total={sum(x.score_contribution for x in v13):.0f})") if all(x.score_contribution>0 for x in v13) and v13 else fail("Contributions",str(v13))

except Exception as e:
    fail("Rule Engine", str(e))

# ── SECTION 4: RISK SCORER ──────────────────────────────────────────────────
section("4 / 7   Risk Scorer")
try:
    from analytics.risk_scoring.risk_scorer import RiskScorer, RiskResult
    from analytics.rule_engine.rule_engine import RuleViolation
    rs = RiskScorer()

    def vio(rid,sev,contrib):
        return RuleViolation(rid,f"Rule {rid}",sev,contrib,"desc")

    r=rs.compute("u","s",0,[],20)
    ok(f"Zero inputs → score=0 sev=Low") if r.risk_score==0 and r.severity=="Low" else fail("Zero inputs",f"{r.risk_score} {r.severity}")

    r=rs.compute("u","s",90,[vio("R32","Critical",45),vio("R30","Critical",40)],20)
    ok(f"High inputs → Critical (score={r.risk_score})") if r.severity=="Critical" and r.risk_score>=90 else fail("High inputs",f"{r.risk_score} {r.severity}")

    bad=False
    for ctmc_v in [0,25,50,75,100]:
        for n in [0,1,3,5]:
            r=rs.compute("u","s",ctmc_v,[vio("R01","M",20)]*n,10)
            if not (0<=r.risk_score<=100): bad=True; fail("0-100 range",f"Got {r.risk_score}"); break
    if not bad: ok("Score always in [0,100] — all input combos")

    r_new=rs.compute("u","s",80,[vio("R01","M",15)],0)
    r_exp=rs.compute("u","s",80,[vio("R01","M",15)],20)
    ok(f"Confidence: new({r_new.confidence}) < exp({r_exp.confidence})") if r_new.confidence<r_exp.confidence else fail("Confidence",f"new={r_new.confidence} exp={r_exp.confidence}")

    r_both=rs.compute("u","s",80,[vio("R30","C",40),vio("R32","C",45)],20)
    r_only=rs.compute("u","s",80,[],20)
    ok(f"Agreement boost: both({r_both.risk_score}) > ctmc-only({r_only.risk_score})") if r_both.risk_score>r_only.risk_score else fail("Boost",f"{r_both.risk_score} not > {r_only.risk_score}")

except Exception as e:
    fail("Risk Scorer", str(e))

# ── SECTION 5: EXPLAINABILITY ───────────────────────────────────────────────
section("5 / 7   Explainability")
try:
    from analytics.explainability.explainer import Explainer
    from analytics.rule_engine.rule_engine import RuleViolation
    exp = Explainer()

    viols=[RuleViolation("R01","After-hours","Medium",15.0,"After hours"),
           RuleViolation("R30","File upload","Critical",40.0,"Upload")]
    states=["Login","File_Access","File_Add","Email","Logout"]
    r=exp.explain("ALT001","testuser",states,viols,82.5,"High",65.0,55.0,0.9)

    ok(f"Summary generated ({len(r.summary)} chars)") if r.summary and len(r.summary)>20 else fail("Summary","Empty")
    ok(f"Reasons generated ({len(r.reasons)})") if r.reasons and len(r.reasons)>=2 else fail("Reasons",f"Got {len(r.reasons)}")
    ok(f"Timeline length={len(r.timeline)}") if len(r.timeline)==len(states) else fail("Timeline len",f"{len(r.timeline)} vs {len(states)}")
    ok(f"Compact ≤ full ({len(r.timeline_compact)} ≤ {len(r.timeline)})") if len(r.timeline_compact)<=len(r.timeline) else fail("Compact","Longer than full")
    ok(f"Actions generated ({len(r.recommended_actions)})") if r.recommended_actions else fail("Actions","Empty")
    ok("Risk context has score/severity") if "82" in r.risk_context or "High" in r.risk_context else fail("Risk context",r.risk_context[:50])
    ok(f"Detection methods ({len(r.detection_methods)})") if r.detection_methods else fail("Methods","Empty")
    ok("Summary mentions user") if "testuser" in r.summary else fail("User in summary","Not found")

    r2=exp.explain("ALT002","u2",["Login","Logout"],[],45.0,"Medium",75.0,0.0,0.8)
    ok("Works with no violations") if r2.summary else fail("No violations","No summary")

    r3=exp.explain("ALT003","u3",["Login"]*3+["Email"]*2+["Logout"],[],30.0,"Low",50.0,0.0,0.7)
    ok(f"Compact deduplicates: 6→{len(r3.timeline_compact)} groups") if len(r3.timeline_compact)<6 else fail("Deduplication",str(r3.timeline_compact))

except Exception as e:
    fail("Explainability", str(e))

# ── SECTION 6: DATA LOADER + MATRIX ─────────────────────────────────────────
section("6 / 7   Data Loader + Population Matrix")
try:
    from analytics.ctmc.population_matrix import load_population_matrix
    from analytics.data.spedia.loader import load_spedia_sessions

    PREPROCESSED = "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv"
    MATRIX_CSV   = "spedia_anomaly_detection/data/ctmc_transition_matrix.csv"

    mx = load_population_matrix(MATRIX_CSV)
    ok(f"Population matrix loaded ({len(mx)} from-states)") if mx else fail("Matrix load","Empty")

    bad=False
    for fs,row in mx.items():
        if abs(sum(row.values())-1.0)>0.01: bad=True; fail("Rows sum 1.0",f"{fs}={sum(row.values()):.4f}"); break
    if not bad: ok("All matrix rows sum to 1.0")

    expected={"Login","File_Access","Email","Browser","Command"}
    found=expected & set(mx.keys())
    ok(f"SPEDIA states in matrix: {found}") if len(found)>=4 else fail("States in matrix",str(found))

    sessions=load_spedia_sessions(PREPROCESSED)
    ok(f"Loader: {len(sessions)} sessions") if len(sessions)>500 else fail("Session count",str(len(sessions)))

    s=sessions[0]
    ok("Session has required keys") if {"session_id","user_id","events","anomaly"}.issubset(s.keys()) else fail("Session keys",str(s.keys()))

    e=sessions[0]["events"][0]
    found_k={"event_id","user_id","timestamp","Activity","Action","Level","CTMC_State"}&e.keys()
    ok(f"Event has required fields ({len(found_k)}/7)") if len(found_k)>=6 else fail("Event fields",str(found_k))

    labels={s["anomaly"] for s in sessions}
    n_anom=sum(1 for s in sessions if s["anomaly"]==1)
    ok(f"Anomaly labels binary: {n_anom} anomalous, {len(sessions)-n_anom} normal") if labels.issubset({0,1}) else fail("Labels",str(labels))

    users={s["user_id"] for s in sessions}
    ok(f"Multiple users: {len(users)} unique") if len(users)>=10 else fail("Users",str(len(users)))

except Exception as e:
    fail("Data Loader / Matrix", str(e))

# ── SECTION 7: FULL PIPELINE ─────────────────────────────────────────────────
section("7 / 7   Full Pipeline — End-to-End")
try:
    from analytics.pipeline.analytics_pipeline import AnalyticsPipeline
    from analytics.data.spedia.loader import load_spedia_sessions
    from analytics.ctmc.population_matrix import load_population_matrix

    sessions   = load_spedia_sessions("spedia_anomaly_detection/data/SPEDIA_preprocessed.csv")
    pop_matrix = load_population_matrix("spedia_anomaly_detection/data/ctmc_transition_matrix.csv")
    pipeline   = AnalyticsPipeline(pop_matrix)

    user_sessions = defaultdict(list)
    for s in sessions: user_sessions[s["user_id"]].append(s)

    test_sessions = []
    for user, u_sessions in user_sessions.items():
        split  = max(1, int(len(u_sessions)*0.8))
        counts = defaultdict(Counter)
        for session in u_sessions[:split]:
            sts=[e.get("CTMC_State","") for e in session["events"] if e.get("CTMC_State")]
            for i in range(len(sts)-1): counts[sts[i]][sts[i+1]]+=1
        matrix={}
        for fs,tc in counts.items():
            tot=sum(tc.values()); matrix[fs]={t:c/tot for t,c in tc.items()}
        if matrix:
            pipeline.user_matrices[user]=matrix
            pipeline.user_session_counts[user]=split
        test_sessions.extend(u_sessions[split:])

    results=[pipeline.process_session(s) for s in test_sessions]
    alerts=[r for r in results if r is not None]

    ok(f"Pipeline ran {len(test_sessions)} sessions without errors")
    ok(f"Alerts generated: {len(alerts)}") if alerts else fail("Alerts generated","Zero alerts")

    normal_test=[s for s in test_sessions if s.get("anomaly")==0]
    normal_silent=sum(1 for s,r in zip(test_sessions,results) if not r and s.get("anomaly")==0)
    ok(f"Normal sessions silent: {normal_silent}/{len(normal_test)}") if normal_silent>0 else fail("Normal silent","None silent")

    if alerts:
        a=alerts[0]
        ok("Output has 4 top-level keys") if {"alert","explanation","model_breakdown","timeline"}.issubset(a.keys()) else fail("Schema keys",str(a.keys()))

        al=a["alert"]
        checks=[isinstance(al["alert_id"],str),isinstance(al["risk_score"],float),
                isinstance(al["severity"],str),al["severity"] in {"Low","Medium","High","Critical"},
                0<=al["risk_score"]<=100, 0<=al["confidence"]<=1]
        ok("Alert field types correct") if all(checks) else fail("Field types",str(checks))

        ex=a["explanation"]
        ok("Explanation populated") if ex.get("summary") and ex.get("reasons") is not None else fail("Explanation",str(list(ex.keys())))

        tl=a["timeline"]
        ok(f"Timeline populated: {len(tl.get('timeline',[]))} steps") if tl.get("timeline") else fail("Timeline","Empty")

    tp=sum(1 for s,r in zip(test_sessions,results) if r and s.get("anomaly")==1)
    fp=sum(1 for s,r in zip(test_sessions,results) if r and s.get("anomaly")==0)
    fn=sum(1 for s,r in zip(test_sessions,results) if not r and s.get("anomaly")==1)
    precision=tp/(tp+fp) if (tp+fp)>0 else 0
    recall=tp/(tp+fn) if (tp+fn)>0 else 0
    f1=2*precision*recall/(precision+recall) if (precision+recall)>0 else 0

    ok(f"F1={f1:.2f} ≥ 0.60  (P={precision:.2f} R={recall:.2f})") if f1>=0.60 else fail("F1≥0.60",f"Got {f1:.2f}")
    ok(f"Precision={precision:.2f} ≥ 0.65") if precision>=0.65 else fail("Precision",f"Got {precision:.2f}")
    ok(f"Recall={recall:.2f} ≥ 0.55") if recall>=0.55 else fail("Recall",f"Got {recall:.2f}")

except Exception as e:
    import traceback
    fail("Full pipeline", traceback.format_exc())

# ── FINAL SUMMARY ────────────────────────────────────────────────────────────
total=passed+failed
print(f"\n{BOLD}{'═'*55}{RESET}")
print(f"{BOLD}  TEST SUMMARY{RESET}")
print(f"{BOLD}{'═'*55}{RESET}")
print(f"  Total  : {total}")
print(f"  {GREEN}Passed : {passed}{RESET}")
print(f"  {RED}Failed : {failed}{RESET}")
if failed==0:
    print(f"\n  {GREEN}{BOLD}ALL TESTS PASSED ✓{RESET}")
    print(f"  Your analytics domain is fully verified.")
else:
    print(f"\n  {RED}{BOLD}FAILURES:{RESET}")
    for name,reason in errors:
        print(f"  {RED}✗ {name}{RESET}")
        print(f"    {reason}")
print(f"{BOLD}{'═'*55}{RESET}\n")
