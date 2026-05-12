import json
import re


PROSECUTION_SIGNALS = {
    "copied": 7,
    "stole": 8,
    "forged": 8,
    "fraud": 8,
    "bribe": 7,
    "kickback": 7,
    "misappropriation": 8,
    "embezz": 8,
    "recorded": 5,
    "written": 4,
    "email": 4,
    "message": 3,
    "documented": 6,
    "admitted": 8,
    "confession": 9,
    "witness": 4,
    "contract": 4,
    "breach": 5,
    "damages": 4,
    "trace": 4,
}

DEFENSE_SIGNALS = {
    "independent": 7,
    "prior work": 7,
    "personal time": 5,
    "consent": 8,
    "authorized": 7,
    "ambiguous": 6,
    "unclear": 5,
    "no intent": 7,
    "mistake": 5,
    "alibi": 9,
    "self-defense": 9,
    "coerced": 7,
    "duress": 7,
    "mitigate": 4,
    "substantial performance": 7,
    "independently built": 8,
    "publicly known": 6,
    "reasonable": 4,
    "lawful": 5,
}

UNCERTAINTY_SIGNALS = {
    "alleges": 4,
    "alleged": 4,
    "claims": 3,
    "denies": 4,
    "disputed": 5,
    "conflicting": 5,
    "unclear": 4,
    "apparently": 2,
    "circumstantial": 4,
    "questions remain": 4,
}

CRIMINAL_SIGNALS = (
    "arrest", "murder", "assault", "theft", "robbery", "fraud",
    "forgery", "kidnap", "charged", "prosecution", "criminal",
    "police", "guilty", "indictment",
)

DEMO_CASES = {
    "code_theft": {
        "markers": (
            "40,000 lines of proprietary source code",
            "competing startup",
            "$2.5m in damages",
        ),
        "research": (
            "Core issues:\n"
            "- Whether the engineer copied or retained protected proprietary code before departure.\n"
            "- Whether the disputed material qualifies as confidential or trade-secret-style information.\n"
            "- Whether the new startup product was independently developed or derived from the former employer's code base.\n"
            "- Whether the employer can show causation, damages, and grounds for injunctive relief.\n\n"
            "Governing principles:\n"
            "- Source-code disputes usually turn on confidentiality, access, similarity, and proof of use in a competing product.\n"
            "- A plaintiff with documented copying, access history, and overlap between products usually has a strong liability pathway.\n"
            "- A defendant can resist liability by showing independent development, prior authorship, or lack of protectable secrecy.\n"
            "- Injunctive relief often depends on ongoing use, competitive harm, and the adequacy of monetary relief.\n\n"
            "Key evidence tensions:\n"
            "- The employer alleges copying of 40,000 lines, which is a substantial quantity and supports seriousness.\n"
            "- The engineer claims independent development during personal time, which goes to authorship and intent.\n"
            "- The startup timeline creates pressure because the competing product followed shortly after departure.\n"
            "- The most important factual question is whether the employer can connect specific code overlap to the new product.\n\n"
            "Pressure points for both sides:\n"
            "- The employer must move beyond accusation and show specific overlap, access, and use.\n"
            "- The engineer must explain the timing and demonstrate clean, independent creation records."
        ),
        "defense": {
            "opening": (
                "Theory of the case:\n"
                "- The engineer's position is that the new product was independently built and not copied from the former employer.\n"
                "- Similarity alone does not establish theft when engineers work in the same domain and solve similar product problems.\n\n"
                "Evidentiary concerns:\n"
                "- The employer still has to prove that the disputed code was actually copied, retained, and used in the new product.\n"
                "- The defense will emphasize personal-time development, prior know-how, and the absence of direct proof tying protected code to the new startup build.\n\n"
                "Legal framing:\n"
                "- If the employer cannot show protectable secrecy, specific copying, and actual competitive use, liability and injunctive relief become much harder to sustain."
            ),
            "rebuttal": (
                "Theory of response:\n"
                "- A large claimed line count sounds dramatic, but the number alone does not prove wrongful use in the current product.\n"
                "- The employer must still separate general engineering knowledge from genuinely protected source material.\n\n"
                "Evidentiary concerns:\n"
                "- The defense will argue that timing and market competition are not substitutes for side-by-side technical proof.\n"
                "- Without clear overlap evidence and a reliable chain from former files to current product code, the accusation remains incomplete.\n\n"
                "Legal framing:\n"
                "- The burden remains on the employer to prove misappropriation, not on the engineer to disprove every inference."
            ),
        },
        "prosecution": {
            "opening": (
                "Liability theory:\n"
                "- The employer's case is that the engineer took proprietary code at departure and used it to accelerate a competing startup launch.\n"
                "- The alleged copying of 40,000 lines is too substantial to dismiss as accidental overlap or ordinary industry know-how.\n\n"
                "Evidentiary support:\n"
                "- The short gap between resignation and launch, combined with the employer's allegation of pre-departure copying, strongly supports an inference of misuse.\n"
                "- If the employer can trace overlapping files, architecture, or unique implementation choices, that is powerful evidence of appropriation.\n\n"
                "Legal framing:\n"
                "- Proprietary source code is the kind of confidential commercial asset that supports damages and injunctive relief when taken for competitive use."
            ),
            "rebuttal": (
                "Liability theory:\n"
                "- Independent development is the defense label, but it does not explain why a competing product emerged so quickly after alleged mass copying.\n"
                "- The prosecution will argue that the sequence of events makes lawful coincidence far less plausible.\n\n"
                "Evidentiary support:\n"
                "- Personal-time work and general skill do not excuse retention or use of protected code from the former employer.\n"
                "- If unique code structure or specific implementation choices carried over, the defense narrative weakens sharply.\n\n"
                "Legal framing:\n"
                "- Once the employer shows protectable code, access, and meaningful overlap, the defense must do more than point to generic technical similarity."
            ),
        },
        "scoring": {
            "defense_score": 29,
            "prosecution_score": 71,
            "explanation": "The employer has the stronger position because the allegation involves large-scale copying, rapid competitive use, and a request for injunctive relief tied to source-code misuse.",
            "stronger_side": "prosecution",
        },
        "verdict": {
            "ruling": "Liable",
            "confidence": 76,
            "reasoning": "The prosecution side is stronger because the allegation combines substantial claimed copying, short timing between departure and launch, and a direct competitive-use theory. The defense raises legitimate questions about independent development, but on the present record the employer's narrative is more concrete and commercially grounded.",
            "key_finding": "The claimed scale of copied code and the rapid emergence of a competing product create a strong inference of unauthorized use.",
            "winning_side": "prosecution",
            "cited_basis": "Trade-secret-style misappropriation reasoning, source-code confidentiality, timing, and overlap risk.",
        },
    },
    "contract_breach": {
        "markers": (
            "freelance ux designer",
            "$18,000",
            "accepted the files but refused to pay",
        ),
        "research": (
            "Core issues:\n"
            "- Whether the designer substantially performed under the signed agreement.\n"
            "- Whether the startup can withhold payment based on undocumented expectations outside the creative brief.\n"
            "- Whether the client's continued commercial use of the deliverables supports acceptance and obligation to pay.\n"
            "- Whether damages are straightforward contract compensation or require additional proof.\n\n"
            "Governing principles:\n"
            "- Contract disputes usually center on the agreed scope, delivery, acceptance, and whether performance matched the written brief.\n"
            "- A party that accepts deliverables and uses them commercially often faces a strong obligation to pay absent a documented defect or reservation.\n"
            "- Undocumented internal expectations are generally weaker than signed scope language and actual acceptance conduct.\n"
            "- Substantial performance can support recovery even when minor disputes remain.\n\n"
            "Key evidence tensions:\n"
            "- The designer says the work matched the signed brief, which supports performance.\n"
            "- The startup claims dissatisfaction, but the dispute appears tied to undocumented expectations.\n"
            "- Commercial use for six weeks is a significant fact because it suggests practical acceptance.\n"
            "- The case likely turns on the written brief and the startup's conduct after delivery.\n\n"
            "Pressure points for both sides:\n"
            "- The designer should anchor the case in the signed brief, delivery record, and ongoing use.\n"
            "- The startup must identify specific contractual deficiencies rather than broad after-the-fact disappointment."
        ),
        "defense": {
            "opening": (
                "Theory of the case:\n"
                "- The startup will argue that delivery alone is not enough if the output did not satisfy the contractual standard the parties intended.\n"
                "- The defense position is that payment can be contested when the deliverables materially miss the expected business needs.\n\n"
                "Evidentiary concerns:\n"
                "- The defense will try to frame the dispute as a quality and fit problem rather than an outright refusal to pay for accepted work.\n"
                "- It may also argue that internal review revealed deficiencies that were not obvious at the moment files were first received.\n\n"
                "Legal framing:\n"
                "- If the startup can show material nonconformity with the agreed deliverables, it may resist full payment or argue for cure."
            ),
            "rebuttal": (
                "Theory of response:\n"
                "- Use of the assets is relevant, but continued use does not automatically waive every objection if the startup believed the work remained incomplete or commercially imperfect.\n"
                "- The defense will argue that acceptance conduct must still be read against the parties' full expectations.\n\n"
                "Evidentiary concerns:\n"
                "- The startup will press for detail on whether every required deliverable was actually provided in usable form.\n"
                "- It will also argue that internal dissatisfaction was not invented later, but reflected a genuine mismatch with brand needs.\n\n"
                "Legal framing:\n"
                "- The designer still bears the burden of showing substantial performance under the actual contract, not just delivery in a broad sense."
            ),
        },
        "prosecution": {
            "opening": (
                "Liability theory:\n"
                "- The plaintiff's contract case is straightforward: the designer delivered the agreed brand system, the startup accepted the files, and then used them commercially without paying the promised $18,000.\n"
                "- That sequence strongly supports breach.\n\n"
                "Evidentiary support:\n"
                "- The signed creative brief is the key benchmark, and the designer says the deliverables matched it.\n"
                "- The startup's six weeks of commercial use is powerful evidence of acceptance and benefit.\n\n"
                "Legal framing:\n"
                "- A client cannot substitute undocumented internal preferences for the actual written scope after taking and using the work."
            ),
            "rebuttal": (
                "Liability theory:\n"
                "- The startup's dissatisfaction defense is weak because it points to undocumented expectations rather than clear contractual defects.\n"
                "- Continued commercial use is not just incidental conduct; it shows the deliverables had value and were accepted in practice.\n\n"
                "Evidentiary support:\n"
                "- If the startup truly believed the work was unusable or materially deficient, its strongest move would not have been to deploy the assets commercially.\n"
                "- That conduct undercuts the claim that payment can be withheld entirely.\n\n"
                "Legal framing:\n"
                "- Contract law generally protects the party that performed to the written brief and delivered work the client then used."
            ),
        },
        "scoring": {
            "defense_score": 24,
            "prosecution_score": 76,
            "explanation": "The designer's side is stronger because the facts emphasize delivery, practical acceptance, and commercial use despite nonpayment.",
            "stronger_side": "prosecution",
        },
        "verdict": {
            "ruling": "Liable",
            "confidence": 79,
            "reasoning": "The plaintiff has the stronger contract case because the deliverables were provided, the files were accepted, and the startup used the work commercially. Undocumented internal expectations are substantially weaker than the signed brief and the client's own acceptance conduct.",
            "key_finding": "Commercial use of the delivered brand assets strongly supports acceptance and the obligation to pay.",
            "winning_side": "prosecution",
            "cited_basis": "Contract-performance analysis focused on written scope, acceptance, and nonpayment.",
        },
    },
    "wrongful_termination": {
        "markers": (
            "11 years of tenure",
            "hostile work environment",
            "cost-reduction restructuring",
        ),
        "research": (
            "Core issues:\n"
            "- Whether the employee engaged in protected activity by filing a formal HR complaint.\n"
            "- Whether the termination eight days later supports an inference of retaliation.\n"
            "- Whether the employer's restructuring explanation is legitimate or pretextual.\n"
            "- Whether the employee's spotless record and unique role make the employer's explanation less credible.\n\n"
            "Governing principles:\n"
            "- Retaliation claims usually examine protected activity, adverse action, temporal proximity, and pretext.\n"
            "- A close timing link between complaint and termination can be powerful, especially when paired with a clean performance history.\n"
            "- Employers may defend with a legitimate restructuring rationale, but that rationale can be tested for consistency and even-handedness.\n"
            "- The key legal question is often whether the stated business reason is genuine or a cover for retaliation.\n\n"
            "Key evidence tensions:\n"
            "- The employee has strong timing evidence because termination followed only eight days after the complaint.\n"
            "- The employer can point to a broader restructuring that affected 12 employees, which gives it a nonretaliatory explanation.\n"
            "- The employee's spotless record and long tenure make sudden termination more suspicious.\n"
            "- The dispute likely turns on whether the employee's role was selected for legitimate business reasons or because she complained.\n\n"
            "Pressure points for both sides:\n"
            "- The employee should focus on timing, performance history, and evidence that her selection was not neutral.\n"
            "- The employer must show specific restructuring criteria and consistent treatment across affected staff."
        ),
        "defense": {
            "opening": (
                "Theory of the case:\n"
                "- The employer's position is that the termination was part of a legitimate cost-reduction restructuring affecting multiple employees, not a retaliatory act.\n"
                "- Timing alone does not convert a workforce decision into unlawful retaliation.\n\n"
                "Evidentiary concerns:\n"
                "- The defense will emphasize that 12 employees were affected, which cuts against the idea that the plaintiff alone was targeted.\n"
                "- It will also argue that long tenure and a positive record do not immunize an employee from organizational restructuring.\n\n"
                "Legal framing:\n"
                "- If the employer can show consistent business criteria for the layoffs, the retaliation inference weakens materially."
            ),
            "rebuttal": (
                "Theory of response:\n"
                "- The employee relies heavily on the eight-day timeline, but close timing is only one part of the analysis and does not automatically prove retaliatory intent.\n"
                "- A real restructuring can coincide with protected activity without being caused by it.\n\n"
                "Evidentiary concerns:\n"
                "- The defense will argue that the broader reduction in force is objective evidence of a business process larger than this individual complaint.\n"
                "- It will also press for proof that similarly situated employees were treated differently or that the restructuring explanation shifted over time.\n\n"
                "Legal framing:\n"
                "- Without stronger evidence of pretext, the court may defer to the employer's documented business rationale."
            ),
        },
        "prosecution": {
            "opening": (
                "Liability theory:\n"
                "- The plaintiff's strongest point is retaliation: a spotless employee with 11 years of tenure was terminated only eight days after filing a formal HR complaint about a hostile work environment.\n"
                "- That timing is highly suspicious and supports an inference of cause-and-effect.\n\n"
                "Evidentiary support:\n"
                "- The plaintiff can pair the timing evidence with her clean record and unique role to argue that the restructuring rationale was pretextual.\n"
                "- A legitimate reduction in force should be supported by clear selection criteria, not a sudden termination immediately after protected activity.\n\n"
                "Legal framing:\n"
                "- Retaliation law is designed to prevent exactly this kind of adverse action after an employee invokes internal complaint protections."
            ),
            "rebuttal": (
                "Liability theory:\n"
                "- The employer's reference to 12 affected employees does not answer the key question: why was this employee selected immediately after a formal complaint?\n"
                "- A broader restructuring can still be used as cover for retaliatory targeting.\n\n"
                "Evidentiary support:\n"
                "- The employee's strong history and the short timeline make the employer's explanation harder to accept at face value.\n"
                "- Unless the employer can show neutral selection criteria and consistent application, the restructuring story remains vulnerable.\n\n"
                "Legal framing:\n"
                "- Where timing, record, and selection context point in the same direction, retaliation becomes the more persuasive account."
            ),
        },
        "scoring": {
            "defense_score": 34,
            "prosecution_score": 66,
            "explanation": "The employee's side is stronger because the record emphasizes protected activity followed by very close termination timing and a strong prior performance history.",
            "stronger_side": "prosecution",
        },
        "verdict": {
            "ruling": "Liable",
            "confidence": 73,
            "reasoning": "The prosecution side is stronger because the eight-day gap between the HR complaint and the termination creates a substantial retaliation inference, especially when combined with the employee's long tenure and strong record. The restructuring explanation is plausible, but on the present facts it is not strong enough to fully neutralize the pretext concern.",
            "key_finding": "The close timing between protected activity and termination is the most significant indicator of retaliatory motive.",
            "winning_side": "prosecution",
            "cited_basis": "Retaliation-style analysis focused on protected activity, temporal proximity, and pretext.",
        },
    },
    "financial_fraud": {
        "markers": (
            "licensed financial advisor directed six clients",
            "12% equity stake",
            "general disclosure clause",
        ),
        "research": (
            "Core issues:\n"
            "- Whether the advisor breached fiduciary or advisory duties by failing to disclose a personal 12% equity stake in the fund's general partner.\n"
            "- Whether the omission was material because it could affect how clients judged the recommendation.\n"
            "- Whether the general disclosure clause was specific enough to cover this exact conflict.\n"
            "- Whether client losses were caused by the undisclosed conflict and recommendation, or mainly by the fund's later collapse.\n\n"
            "Governing principles:\n"
            "- Financial advisors typically owe duties of candor, loyalty, and fair dealing when recommending investments.\n"
            "- A personal financial interest in a recommended product is usually a material conflict that requires clear, specific disclosure.\n"
            "- A broad boilerplate disclosure often does not excuse failure to disclose a known, direct, and substantial conflict.\n"
            "- Fraud or misrepresentation theories usually focus on material omission, client reliance, causation, and damages.\n"
            "- Even if intentional fraud is disputed, the facts can still support breach of fiduciary duty, negligent misrepresentation, or unfair advisory conduct.\n\n"
            "Key evidence tensions:\n"
            "- Strong fact for liability: undisclosed ownership interest in the fund's general partner.\n"
            "- Strong fact for damages: six clients invested $620,000 and lost about $410,000.\n"
            "- Main defense fact: the advisor says the onboarding agreement had a general conflict disclosure clause.\n"
            "- Main defense fact: he claims he acted in good faith based on projected returns.\n"
            "- Weakness for defense: the clause appears general, while the conflict here was concrete and personal.\n\n"
            "Pressure points for both sides:\n"
            "- Prosecution pressure point: prove the omission mattered to the clients' decision-making, not just that the fund failed.\n"
            "- Defense pressure point: explain why a specific personal stake was never expressly disclosed."
        ),
        "defense": {
            "opening": (
                "Theory of the case:\n"
                "- Poor investment outcome does not automatically establish fraud or intentional misconduct.\n"
                "- The advisor can argue that the recommendation was made in good faith based on the fund's projected returns at the time.\n\n"
                "Evidentiary concerns:\n"
                "- The defense will emphasize that the losses were caused by the fund's collapse, not simply by the existence of a conflict.\n"
                "- It will also rely on the onboarding disclosure language to argue that potential conflicts were not concealed in a complete sense.\n\n"
                "Legal framing:\n"
                "- Even if disclosure could have been more specific, the defense will resist turning that point into full fraud liability without stronger proof of intent and causation."
            ),
            "rebuttal": (
                "Theory of response:\n"
                "- The undisclosed stake is uncomfortable, but the decisive question is whether that omission legally caused the clients' losses and whether the general disclosures were insufficient as a matter of law.\n"
                "- The defense will argue that hindsight should not replace a disciplined causation analysis.\n\n"
                "Evidentiary concerns:\n"
                "- The record still needs proof that a more explicit disclosure would have changed the clients' decisions.\n"
                "- The defense can frame the case as a disclosure lapse at most, rather than deliberate fraud.\n\n"
                "Legal framing:\n"
                "- A finding short of intentional fraud remains more consistent with the defense reading of the record."
            ),
        },
        "prosecution": {
            "opening": (
                "Liability theory:\n"
                "- This is a direct undisclosed-conflict case: the advisor steered clients into a fund while secretly holding a 12% equity stake in the fund's general partner.\n"
                "- That personal financial interest created divided loyalty and undermined the neutrality of the recommendation.\n\n"
                "Evidentiary support:\n"
                "- A reasonable client would consider that stake important before investing substantial funds.\n"
                "- Six clients invested $620,000 and later lost about $410,000, making the omission economically significant and concrete.\n\n"
                "Legal framing:\n"
                "- A vague general disclosure clause does not substitute for explicit disclosure of a known, substantial personal conflict."
            ),
            "rebuttal": (
                "Liability theory:\n"
                "- The defense relies on boilerplate disclosure language and good-faith language, but neither cures a specific undisclosed financial interest tied to the recommended investment.\n"
                "- If the advice were fully client-centered, there would have been no reason to omit the stake.\n\n"
                "Evidentiary support:\n"
                "- The prosecution does not need to prove the advisor caused the fund to collapse; it needs to show that the recommendation process was tainted by undisclosed self-interest.\n"
                "- That omission goes directly to trust, reliance, and the fairness of the transaction.\n\n"
                "Legal framing:\n"
                "- Material nondisclosure and breach of loyalty strongly support liability on this record."
            ),
        },
        "scoring": {
            "defense_score": 22,
            "prosecution_score": 78,
            "explanation": "The prosecution side is stronger because the record centers on a specific undisclosed financial conflict, while the defense relies mainly on general disclosure language and causation objections.",
            "stronger_side": "prosecution",
        },
        "verdict": {
            "ruling": "Advisor liable for financial misconduct / breach of fiduciary duty",
            "confidence": 81,
            "reasoning": "The strongest fact is the advisor's failure to disclose his 12% equity stake in the fund's general partner while directing clients to invest. A general disclosure clause about possible conflicts does not adequately disclose a concrete personal financial interest of this kind. Even allowing for uncertainty about the fund's collapse itself, the undisclosed conflict materially weakens the good-faith defense and strongly supports liability.",
            "key_finding": "The advisor's undisclosed ownership interest was a material conflict that should have been expressly disclosed before the investment recommendations were made.",
            "winning_side": "prosecution",
            "cited_basis": "Conflict-of-interest disclosure duties, client reliance, and material omission reasoning.",
        },
    },
}


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, int(value)))


def parse_json_object(raw: str) -> dict | None:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def infer_case_domain(case_text: str) -> str:
    lowered = case_text.lower()
    if any(token in lowered for token in CRIMINAL_SIGNALS):
        return "criminal"
    return "civil"


def identify_demo_case(case_text: str) -> str | None:
    normalized = " ".join((case_text or "").strip().lower().split())
    for name, payload in DEMO_CASES.items():
        if all(marker in normalized for marker in payload["markers"]):
            return name
    return None


def extract_labeled_section(prompt: str, label: str, stop_labels: list[str]) -> str:
    escaped_label = re.escape(label)
    stop_pattern = "|".join(re.escape(item) for item in stop_labels)
    pattern = rf"{escaped_label}\n(.*?)(?=\n\n(?:{stop_pattern})\n|\Z)"
    match = re.search(pattern, prompt, flags=re.DOTALL)
    return match.group(1).strip() if match else ""


def heuristic_research_brief(case: str, retrieved_context: str = "") -> str:
    demo_name = identify_demo_case(case)
    if demo_name:
        return str(DEMO_CASES[demo_name]["research"])

    domain = infer_case_domain(case)
    context_note = "The retrieved materials appear to supply supporting legal context." if retrieved_context.strip() else "The current fallback brief relies primarily on the case narrative."
    issues = (
        "liability elements, intent or knowledge, reliability of the available proof, and causation or damages"
        if domain == "civil"
        else "the charged elements, intent, reliability of the proof, and whether reasonable doubt remains"
    )
    return (
        "Core issues:\n"
        f"- The main dispute turns on {issues}.\n"
        "- The record appears to contain both direct allegations and contested defensive explanations.\n"
        "- The fact finder will likely focus on what can be proven concretely rather than what is merely asserted.\n\n"
        "Governing principles:\n"
        "- The strongest side will usually be the one that ties the facts to a clear legal theory and supports it with reliable evidence.\n"
        "- Timing, documents, admissions, and consistent third-party proof typically carry more weight than generalized accusations.\n"
        f"- {context_note}\n\n"
        "Key evidence tensions:\n"
        "- One side appears to rely on a concentrated set of adverse facts, while the other side relies on doubt, alternative explanation, or causation limits.\n"
        "- The likely weakness in the case is the gap between allegation and proof if the factual record is not tightly documented.\n\n"
        "Pressure points for both sides:\n"
        "- The prosecution or plaintiff should identify the clearest factual anchors and why they satisfy the legal elements.\n"
        "- The defense should challenge proof quality, intent, causation, and any leap from suspicion to conclusion."
    )


def heuristic_argument(
    side: str,
    case: str,
    research: str = "",
    opposing_argument: str = "",
    round_name: str = "opening",
) -> str:
    demo_name = identify_demo_case(case)
    if demo_name:
        side_block = DEMO_CASES[demo_name][side]
        if isinstance(side_block, dict):
            return str(side_block["rebuttal" if round_name == "rebuttal" else "opening"])

    if side == "defense":
        if round_name == "opening":
            return (
                "Theory of the case:\n"
                "- The defense position is that the current record leaves meaningful factual and legal uncertainty unresolved.\n"
                "- Adverse outcome or suspicion alone is not enough to prove liability.\n\n"
                "Evidentiary concerns:\n"
                "- The defense will challenge whether the opposing side can connect allegation to reliable, specific proof.\n"
                "- It will also emphasize alternative explanations, intent gaps, or causation limits where available.\n\n"
                "Legal framing:\n"
                "- The burden remains on the opposing side to prove its theory with more than inference and hindsight."
            )
        return (
            "Theory of response:\n"
            "- The defense will argue that the opposing side overstates what the record actually proves.\n"
            "- Strong rhetoric does not cure missing proof on intent, causation, or legal fit.\n\n"
            "Evidentiary concerns:\n"
            "- The defense can accept that some facts are uncomfortable while still arguing they do not justify the full liability theory advanced.\n"
            "- The remaining ambiguities should be resolved cautiously rather than against the defendant by default.\n\n"
            "Legal framing:\n"
            "- Where material uncertainty remains, the safer legal course is a narrower or defense-favoring outcome."
        )

    if round_name == "opening":
        return (
            "Liability theory:\n"
            "- The prosecution or plaintiff position is that the case narrative already points toward a concrete legal wrong rather than a neutral misunderstanding.\n"
            "- The most important facts can be organized into a direct theory of liability.\n\n"
            "Evidentiary support:\n"
            "- The opposing side's explanations do not fully answer the strongest adverse facts in the record.\n"
            "- Documents, timing, or economically significant consequences likely strengthen the claim.\n\n"
            "Legal framing:\n"
            "- When the record is read as a whole, the more persuasive interpretation is that liability should attach."
        )
    return (
        "Liability theory:\n"
        "- The prosecution or plaintiff will argue that the defense explanation does not adequately neutralize the strongest facts in the case.\n"
        "- The fallback analysis still favors the side with the clearer factual chain and fewer speculative leaps.\n\n"
        "Evidentiary support:\n"
        "- The defense can raise doubt, but doubt must connect to the actual proof rather than rest on abstract possibility.\n"
        "- The record remains stronger where conduct, timing, and consequence align with the liability theory.\n\n"
        "Legal framing:\n"
        "- The more coherent reading of the record still supports a plaintiff or prosecution-leaning result."
    )


def _count_weighted(text: str, signals: dict[str, int]) -> tuple[int, list[str]]:
    lowered = text.lower()
    score = 0
    reasons: list[str] = []
    for phrase, weight in signals.items():
        matches = lowered.count(phrase)
        if matches:
            score += matches * weight
            reasons.append(phrase)
    return score, reasons[:4]


def _compact_reason(terms: list[str]) -> str:
    if not terms:
        return ""
    cleaned = [term.replace("_", " ") for term in terms[:3]]
    if len(cleaned) == 1:
        return cleaned[0]
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def heuristic_scoring(case: str, research: str, defense: str, prosecution: str) -> dict:
    demo_name = identify_demo_case(case)
    if demo_name:
        return dict(DEMO_CASES[demo_name]["scoring"])

    case_score_p, case_reasons_p = _count_weighted(case, PROSECUTION_SIGNALS)
    case_score_d, case_reasons_d = _count_weighted(case, DEFENSE_SIGNALS)
    pros_score, pros_reasons = _count_weighted(prosecution, PROSECUTION_SIGNALS)
    def_score, def_reasons = _count_weighted(defense, DEFENSE_SIGNALS)
    uncertainty, uncertainty_reasons = _count_weighted(
        "\n".join([case, research, defense, prosecution]),
        UNCERTAINTY_SIGNALS,
    )

    prosecution_weight = pros_score + case_score_p // 2 + len(prosecution.split()) // 18
    defense_weight = def_score + case_score_d // 2 + len(defense.split()) // 18
    advantage = prosecution_weight - defense_weight
    baseline = 58 - min(10, uncertainty)

    prosecution_score = clamp(round(baseline + advantage * 0.9), 28, 85)
    defense_score = clamp(round(baseline - advantage * 0.9), 28, 85)

    if abs(prosecution_score - defense_score) <= 4:
        stronger_side = "balanced"
    else:
        stronger_side = "prosecution" if prosecution_score > defense_score else "defense"

    explanation_parts: list[str] = []
    if prosecution_score > defense_score:
        signal_text = _compact_reason(pros_reasons or case_reasons_p)
        if signal_text:
            explanation_parts.append(
                f"The prosecution side is stronger because the record emphasizes {signal_text}."
            )
    elif defense_score > prosecution_score:
        signal_text = _compact_reason(def_reasons or case_reasons_d)
        if signal_text:
            explanation_parts.append(
                f"The defense side is stronger because the facts emphasize {signal_text}."
            )
    if uncertainty_reasons:
        explanation_parts.append(
            f"Residual uncertainty remains due to {_compact_reason(uncertainty_reasons)}."
        )
    if not explanation_parts:
        explanation_parts.append(
            "Both sides are close on the current record, so the fallback scorer treated the dispute as comparatively balanced."
        )

    return {
        "defense_score": defense_score,
        "prosecution_score": prosecution_score,
        "explanation": " ".join(explanation_parts),
        "stronger_side": stronger_side,
    }


def heuristic_verdict(case: str, research: str, scoring: dict) -> dict:
    demo_name = identify_demo_case(case)
    if demo_name:
        return dict(DEMO_CASES[demo_name]["verdict"])

    prosecution_score = int(scoring.get("prosecution_score", 50))
    defense_score = int(scoring.get("defense_score", 50))
    advantage = prosecution_score - defense_score
    uncertainty, uncertainty_reasons = _count_weighted("\n".join([case, research]), UNCERTAINTY_SIGNALS)
    evidence_strength, prosecution_reasons = _count_weighted("\n".join([case, research]), PROSECUTION_SIGNALS)
    defense_strength, defense_reasons = _count_weighted(case, DEFENSE_SIGNALS)
    domain = infer_case_domain(case)

    if advantage >= 8:
        ruling = "Guilty" if domain == "criminal" else "Liable"
        winning_side = "prosecution"
        key_finding = _compact_reason(prosecution_reasons) or "Documented evidence trends toward the prosecution side."
    elif advantage <= -8:
        ruling = "Not Guilty" if domain == "criminal" else "Not Liable"
        winning_side = "defense"
        key_finding = _compact_reason(defense_reasons) or "The defense account leaves material doubt unresolved."
    else:
        ruling = "Undetermined"
        winning_side = "balanced"
        key_finding = "The competing arguments remain too close to resolve decisively."

    confidence = clamp(
        52 + abs(advantage) * 2 + min(8, evidence_strength // 3) - min(10, uncertainty * 2),
        48,
        90,
    )

    reasoning_parts: list[str] = [
        f"The fallback judge compared the argument scores ({defense_score} for defense versus {prosecution_score} for prosecution)."
    ]
    if winning_side == "prosecution":
        reasoning_parts.append(
            "The prosecution side carries more concrete support from the case narrative and retrieved context."
        )
    elif winning_side == "defense":
        reasoning_parts.append(
            "The defense side preserves enough factual or intent-based doubt to outweigh the opposing case."
        )
    else:
        reasoning_parts.append(
            "Neither side separates itself enough on the present record to justify a decisive ruling."
        )
    if uncertainty_reasons:
        reasoning_parts.append(
            f"Confidence is moderated by {_compact_reason(uncertainty_reasons)}."
        )

    return {
        "ruling": ruling,
        "confidence": confidence,
        "reasoning": " ".join(reasoning_parts),
        "key_finding": key_finding,
        "winning_side": winning_side,
        "cited_basis": "Fallback comparative reasoning using the retrieved context and argument strength signals.",
    }


def heuristic_appeal(case: str, verdict: dict, scoring: dict | None = None) -> dict:
    scoring = scoring or {}
    prosecution_score = int(scoring.get("prosecution_score", 50))
    defense_score = int(scoring.get("defense_score", 50))
    confidence = int(verdict.get("confidence", 50))
    gap = abs(prosecution_score - defense_score)

    grounds: list[str] = []
    if gap <= 6 and confidence >= 72:
        grounds.append("Confidence appears disproportionate to the closeness of the competing arguments")
    if verdict.get("ruling") in {"Liable", "Guilty", "Not Liable", "Not Guilty"} and confidence <= 58:
        grounds.append("The verdict is decisive but the confidence level suggests unresolved doubt")
    if len(str(verdict.get("reasoning", "")).split()) < 18:
        grounds.append("The verdict explanation is too compressed to show a full reasoning path")
    if not verdict.get("key_finding"):
        grounds.append("The verdict lacks a clear key factual finding")

    uncertainty, uncertainty_reasons = _count_weighted(case, UNCERTAINTY_SIGNALS)
    if uncertainty >= 6 and confidence >= 70:
        grounds.append("The case narrative contains disputed facts that may warrant a more cautious confidence level")

    appeal_warranted = bool(grounds)
    if not appeal_warranted:
        recommended_action = "Uphold verdict"
        appeal_strength = clamp(18 + max(0, 5 - gap), 10, 35)
    elif any("confidence" in ground.lower() for ground in grounds):
        recommended_action = "Reduce confidence score"
        appeal_strength = clamp(55 + len(grounds) * 6, 45, 78)
    else:
        recommended_action = "Remand for reconsideration"
        appeal_strength = clamp(50 + len(grounds) * 7, 45, 82)

    if appeal_warranted:
        dissenting_view = (
            "A narrower reading of the record would call for a more cautious outcome or a fuller explanation before the ruling stands."
        )
    else:
        dissenting_view = (
            "An appellate panel could ask for fuller phrasing, but the present result is broadly supportable on this record."
        )
    if uncertainty_reasons and appeal_warranted:
        dissenting_view = (
            f"A dissent could emphasize {_compact_reason(uncertainty_reasons)} and argue that the verdict should be revisited with a more restrained confidence assessment."
        )

    return {
        "appeal_warranted": appeal_warranted,
        "grounds": grounds,
        "recommended_action": recommended_action,
        "appeal_strength": appeal_strength,
        "dissenting_view": dissenting_view,
    }
