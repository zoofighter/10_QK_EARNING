"""
AI Report Agent Service
Coordinates multi-company cross-referencing, financial metric retrieval,
earnings call transcript excerpts, and structured report synthesis.
Supports both Google Gemini (direct REST API) and local Ollama (Qwen 2.5).
"""
import os
import json
import urllib.request
import urllib.error
import subprocess
import shutil
from typing import Dict, Any, List, Optional
from app.models.database import query_db

REPORT_TEMPLATES = {
    "cross_chain": {
        "title": "밸류체인 교차 비교 심층 리포트 (추천)",
        "chapters": [
            "1. Executive Summary (핵심 결론 및 시사점 3줄 요약)",
            "2. 대상 기업 최근 실적 분석 (매출액, 영업이익, 영업이익률, CapEx 확정치 테이블)",
            "3. 밸류체인 전·후방 기업과의 교차 대조 (경쟁사 점유율 및 고객사 수요)",
            "4. 어닝콜 경영진 발언 및 시장 핵심 의구심(Q&A) 검증",
            "5. 산업 선행지표(TSMC 월매출, 메모리 현물가, 수출통계, GPU 렌탈가) 연계 시그널",
            "6. 향후 실적 전망 및 리스크 요인"
        ]
    },
    "beat_miss": {
        "title": "어닝 서프라이즈 (Beat/Miss) 긴급 점검 리포트",
        "chapters": [
            "1. 실적 결과 요약 (컨센서스 대비 매출/EPS 서프라이즈율 %)",
            "2. 어닝 발표 직후 1일/5일 주가 반응 및 시장 평가",
            "3. 호실적/부진을 견인한 핵심 요인 및 부문별 실적",
            "4. 경영진의 다음 분기 가이던스(Guidance) 변경 내역",
            "5. 투자 의견 및 주요 체크포인트"
        ]
    },
    "executive_brief": {
        "title": "경영진/의사결정자용 1페이지 Executive Briefing",
        "chapters": [
            "1. Key Takeaways (한눈에 보는 3대 핵심 이슈)",
            "2. 밸류체인 내 핵심 재무/투자 지표 현황",
            "3. 경쟁사 동향 및 전략적 위협 요인",
            "4. 단기 대응 권고사항 (Action Items)"
        ]
    }
}


class ReportAgent:
    """Agentic RAG Engine for cross-company financial and transcript synthesis."""

    def __init__(self, engine: str = "gemini", model_name: Optional[str] = None):
        self.engine = engine.lower()  # 'gemini' | 'ollama' | 'opencode'
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

        if not model_name:
            if self.engine == "gemini":
                self.model_name = "gemini-2.5-flash"
            elif self.engine == "opencode":
                self.model_name = "opencode/muse-spark-1.3-contributor-free"
            else:
                self.model_name = "qwen2.5:7b"
        else:
            self.model_name = model_name

    # =========================================================================
    # 1. Database Tools (Functions callable by the Agent)
    # =========================================================================

    @staticmethod
    def tool_get_quarterly_financials(ticker: str, limit: int = 4) -> Dict[str, Any]:
        """Fetch quarterly financial series (revenue, op margin, capex, datacenter rev)."""
        from app.services.financial_service import FinancialService

        clean_ticker = ticker.upper().strip()
        fs = FinancialService()
        data = fs.get_quarterly_financials(clean_ticker)

        if data.get("status") != "success":
            return {"error": data.get("message", f"Failed to get financials for {clean_ticker}")}

        series = data.get("series", [])[:limit]
        formatted = []
        for s in series:
            formatted.append({
                "period": s.get("period") or s.get("period_key"),
                "filing_type": s.get("filing_type", "10-Q"),
                "revenue_usd_m": s.get("revenue"),
                "revenue_yoy_pct": s.get("revenue_yoy_pct"),
                "operating_income_usd_m": s.get("operating_income"),
                "op_income_usd_m": s.get("operating_income"),
                "operating_margin_pct": s.get("op_margin_pct"),
                "op_margin_pct": s.get("op_margin_pct"),
                "net_income_usd_m": s.get("net_income"),
                "capex_usd_m": s.get("capex"),
                "datacenter_rev_usd_m": s.get("revenue_datacenter"),
                "datacenter_pct": s.get("revenue_datacenter_pct"),
                "mda_summary": s.get("mda_summary"),
                "fx_rate_label": s.get("fx_rate_label")
            })

        ent = data.get("entity", {})
        return {
            "ticker": clean_ticker,
            "company_name": ent.get("name_ko") or ent.get("name_en") or clean_ticker,
            "layer": ent.get("layer_code", ""),
            "count": len(formatted),
            "series": formatted
        }

    @staticmethod
    def tool_search_transcripts(ticker: str, query: str = "") -> Dict[str, Any]:
        """Search earning call transcripts for remarks, guidance, and analyst Q&As."""
        clean_ticker = ticker.upper().strip()
        entity = query_db("SELECT id, ticker, name_ko FROM entity WHERE ticker = ?", (clean_ticker,), one=True)
        if not entity:
            return {"error": f"Entity not found for ticker: {clean_ticker}"}

        rows = query_db(
            """
            SELECT id, fiscal_year, fiscal_quarter, call_date, transcript_text, source_url
            FROM earning_call
            WHERE entity_id = ?
            ORDER BY call_date DESC, fiscal_year DESC
            LIMIT 2
            """,
            (entity["id"],)
        )

        if not rows:
            return {"ticker": clean_ticker, "transcripts_found": 0, "message": "No transcripts in database."}

        results = []
        q_lower = query.lower().strip() if query else ""

        for r in rows:
            full_text = r["transcript_text"] or ""
            period = f"{r['fiscal_year']}-{r['fiscal_quarter']}"
            call_date = r["call_date"]

            matched_excerpts = []
            if q_lower:
                # Find occurrences of query
                paragraphs = full_text.split("\n\n")
                for p in paragraphs:
                    if q_lower in p.lower():
                        matched_excerpts.append(p.strip())
                        if len(matched_excerpts) >= 4:
                            break

            # Fallback if no specific query or no matches
            if not matched_excerpts:
                # Provide opening remarks and Q&A excerpt
                matched_excerpts = [full_text[:1200] + "..."]

            results.append({
                "period": period,
                "call_date": call_date,
                "source_url": r.get("source_url"),
                "excerpts": matched_excerpts
            })

        return {
            "ticker": clean_ticker,
            "company_name": entity["name_ko"],
            "transcripts_found": len(results),
            "results": results
        }

    @staticmethod
    def tool_get_consensus_surprise(ticker: str) -> Dict[str, Any]:
        """Retrieve market consensus, beat/miss surprises, and 1-day/5-day stock reactions."""
        clean_ticker = ticker.upper().strip()
        entity = query_db("SELECT id, ticker, name_ko FROM entity WHERE ticker = ?", (clean_ticker,), one=True)
        if not entity:
            return {"error": f"Entity not found for ticker: {clean_ticker}"}

        rows = query_db(
            """
            SELECT fiscal_year, fiscal_quarter, metric_type, consensus_value,
                   actual_value, surprise_pct, beat_miss_status,
                   post_earning_return_1d, post_earning_return_5d
            FROM consensus
            WHERE entity_id = ?
            ORDER BY fiscal_year DESC, fiscal_quarter DESC
            LIMIT 6
            """,
            (entity["id"],)
        )

        return {
            "ticker": clean_ticker,
            "company_name": entity["name_ko"],
            "records": [dict(r) for r in rows]
        }

    @staticmethod
    def tool_get_gpu_rental_prices(gpu_model: str = "H100") -> Dict[str, Any]:
        """Fetch real-time and historical GPU cloud rental spot prices ($/hr)."""
        from app.services.gpu_price_collector import GpuPriceCollector
        collector = GpuPriceCollector()
        clean_model = gpu_model.upper().strip() if gpu_model else "H100"
        
        summary = collector.get_latest_summary()
        history = collector.get_price_history(clean_model, limit=12)
        
        kpi = summary["kpis"].get(clean_model, summary["kpis"].get("H100"))
        
        # Filter matching providers
        providers = [p for p in summary["providers"] if p["model_key"] == clean_model]
        if not providers:
            providers = summary["providers"][:4]

        return {
            "requested_model": clean_model,
            "current_benchmark": kpi,
            "recent_trend": history.get("history", []),
            "providers_quotations": providers
        }

    @staticmethod
    def tool_get_lead_indicators() -> Dict[str, Any]:
        """Fetch leading indicators: memory spot prices, customs export statistics, and GPU rental prices."""
        mem_rows = query_db(
            """
            SELECT indicator_type, date, value, unit, note
            FROM industry_indicator
            WHERE source = 'SPOT_FEED'
            ORDER BY date DESC
            LIMIT 6
            """
        )
        exp_rows = query_db(
            """
            SELECT indicator_type, date, value, unit, note
            FROM industry_indicator
            WHERE source = 'CUSTOMS_KR'
            ORDER BY date DESC
            LIMIT 6
            """
        )
        gpu_rows = query_db(
            """
            SELECT indicator_type, date, value, unit, note
            FROM industry_indicator
            WHERE indicator_type LIKE 'GPU_RENTAL_%'
            ORDER BY date DESC
            LIMIT 6
            """
        )

        return {
            "memory_spot_latest": [dict(r) for r in mem_rows],
            "kr_semiconductor_export_latest": [dict(r) for r in exp_rows],
            "gpu_rental_latest": [dict(r) for r in gpu_rows]
        }

    # =========================================================================
    # 2. Tool Definitions for Function Calling (OpenAI & Gemini Compatible)
    # =========================================================================

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return tool definitions schema."""
        return [
            {
                "name": "get_quarterly_financials",
                "description": "기업의 최근 분기별 매출액, 영업이익(Operating Income 절대액), 영업이익률(OPM %), 순이익, 설비투자(CapEx), 데이터센터 비중, YoY 성장률을 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "기업 티커 심볼 (예: NVDA, 005930.KS, 000660.KS, TSM, MSFT)"},
                        "limit": {"type": "integer", "description": "조회할 최근 분기 수 (기본 4)"}
                    },
                    "required": ["ticker"]
                }
            },
            {
                "name": "search_earning_call_transcripts",
                "description": "특정 기업의 실적발표 컨퍼런스콜 전문에서 경영진 발표문(Remarks) 및 애널리스트 질의응답(Q&A) 발언을 검색합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "기업 티커 심볼 (예: NVDA, 005930.KS, 000660.KS, TSM, MSFT)"},
                        "query": {"type": "string", "description": "검색할 키워드나 쟁점 (예: Blackwell, HBM3E, 수율, CapEx, 솔드아웃, 가이던스)"}
                    },
                    "required": ["ticker"]
                }
            },
            {
                "name": "get_consensus_surprise",
                "description": "기업의 분기별 실적 컨센서스 대비 어닝 서프라이즈(Beat/Miss) 판정 및 실적 발표 후 1일/5일 주가 반응을 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "기업 티커 심볼"}
                    },
                    "required": ["ticker"]
                }
            },
            {
                "name": "get_lead_indicators",
                "description": "글로벌 DRAM/NAND 메모리 현물 가격 추이, 한국 관세청 10일 단위 반도체 수출 잠정치, 및 최신 GPU 렌탈 스팟 가격을 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_gpu_rental_prices",
                "description": "NVIDIA H100, H200, B200, A100 등 주요 AI 가속기의 클라우드 렌탈 스팟 시세($/hr), 30일 가격 추이, 및 공급사(Lambda, RunPod, CoreWeave 등)별 단가를 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "gpu_model": {"type": "string", "description": "GPU 모델명 ('H100', 'H200', 'B200', 'A100' 중 선택, 기본 'H100')"}
                    }
                }
            }
        ]

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch and execute tool against local database."""
        if name == "get_quarterly_financials":
            ticker = args.get("ticker", "NVDA")
            limit = int(args.get("limit", 4))
            return self.tool_get_quarterly_financials(ticker, limit)
        elif name == "search_earning_call_transcripts":
            ticker = args.get("ticker", "NVDA")
            query = args.get("query", "")
            return self.tool_search_transcripts(ticker, query)
        elif name == "get_consensus_surprise":
            ticker = args.get("ticker", "NVDA")
            return self.tool_get_consensus_surprise(ticker)
        elif name == "get_lead_indicators":
            return self.tool_get_lead_indicators()
        elif name == "get_gpu_rental_prices":
            gpu_model = args.get("gpu_model", "H100")
            return self.tool_get_gpu_rental_prices(gpu_model)
        else:
            return {"error": f"Unknown tool: {name}"}

    # =========================================================================
    # 3. Execution Pipeline (Gemini REST & Ollama)
    # =========================================================================

    def generate_report(
        self,
        target_ticker: str,
        peer_tickers: List[str],
        chapters: List[str],
        user_notes: str = "",
        timeframe: str = "latest",
        tone_style: str = "analyst"
    ) -> Dict[str, Any]:
        """
        Orchestrate multi-turn tool calling and synthesize comprehensive report.
        """
        target_ticker = target_ticker.upper().strip()
        peer_tickers = [p.upper().strip() for p in peer_tickers if p.strip()]

        # Tone description
        tone_map = {
            "analyst": "증권사 기관 리서치(Institutional Equity Research) 스타일로 전문적이고 객관적인 격식체(-한다, -이다)를 유지하십시오.",
            "newsletter": "이해하기 쉽고 직관적인 테크 투자 뉴스레터/칼럼 스타일(-합니다)로 흥미진진하게 서술하십시오.",
            "executive": "경영진/C-Level 의사결정자를 위한 1페이지 압축 요약 메모 스타일로 핵심 결론과 불릿 포인트 위주로 작성하십시오."
        }
        tone_instruction = tone_map.get(tone_style, tone_map["analyst"])

        # System Prompt
        system_prompt = f"""당신은 세계 최고 수준의 글로벌 AI 반도체 밸류체인 수석 수석 애널리스트(Chief Equity Research Analyst)입니다.
사용자가 요청한 구조화된 목차와 가설을 바탕으로, 정확한 데이터베이스 팩트 수치를 직접 도구(Tools)를 호출하여 확인한 후 교차 분석 보고서를 작성해야 합니다.

[작성 규칙]
1. 반드시 사용자가 지정한 목차 챕터 순서를 엄격히 준수하여 보고서를 작성하십시오.
2. 메인 분석 대상 기업: {target_ticker}
3. 교차 비교 대상 기업군: {', '.join(peer_tickers) if peer_tickers else '자체 심층 분석'}
4. 문체: {tone_instruction}
5. [필수] 최근 실적 분석 테이블 구성:
   - 대상 기업 실적 분석 챕터에서는 반드시 마크다운 테이블을 작성하십시오.
   - 테이블 컬럼에는 [분기 (Period), 매출액 (Revenue), 매출 YoY(%), 영업이익 (Operating Income), 영업이익률 (OPM %), 설비투자 (CapEx), 데이터센터 비중(%)]을 빠짐없이 포함해야 합니다.
   - 특히 매출액뿐만 아니라 '영업이익' 절대 금액($M 또는 조원/억원)과 '영업이익률(%)'을 반드시 둘 다 명시하십시오.
6. 정확성: 재무 수치는 반드시 도구(Tool)를 통해 가져온 실제 팩트 데이터를 인용해야 하며, 추측으로 임의의 숫자를 지어내지 마십시오.
7. 출처/인용: 어닝콜 발언이나 Q&A를 인용할 때는 발언자(경영진 또는 애널리스트)와 분기를 명시하십시오.
"""

        # Build User Prompt
        chapters_formatted = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(chapters)])
        user_prompt = f"""다음 요청에 따라 심층 분석 보고서를 작성해 주십시오.

[지정된 목차 구성]
{chapters_formatted}

[사용자의 추가 메모 / 분석 가설]
{user_notes if user_notes else "(사용자 수동 메모 없음. 기본 팩트 기반 객관적 분석 진행 요망)"}

먼저 필요한 데이터(대상 기업 {target_ticker} 및 교차 비교 기업들의 재무제표와 어닝콜 발언)를 도구(Tools)를 호출하여 조회한 후, 완결성 있는 고품질 마크다운 보고서를 작성해 주십시오.
"""

        tools_used_log = []

        if self.engine == "gemini":
            report_markdown, tools_used_log = self._run_gemini_agent(system_prompt, user_prompt, tools_used_log)
        elif self.engine == "opencode":
            report_markdown, tools_used_log = self._run_opencode_agent(
                system_prompt, user_prompt, tools_used_log, target_ticker, peer_tickers
            )
        else:
            report_markdown, tools_used_log = self._run_ollama_agent(system_prompt, user_prompt, tools_used_log)

        return {
            "status": "success",
            "engine": self.engine,
            "model": self.model_name,
            "target_ticker": target_ticker,
            "peer_tickers": peer_tickers,
            "tools_used": tools_used_log,
            "report_markdown": report_markdown
        }

    # =========================================================================
    # 4. Engine Implementation: Gemini REST API (2.5 Flash / 3.8 Flash)
    # =========================================================================

    def _run_gemini_agent(
        self, system_prompt: str, user_prompt: str, tools_log: List[Dict[str, Any]]
    ) -> (str, List[Dict[str, Any]]):
        """Execute ReAct tool calling loop against Google Gemini REST API with retry and fallback."""
        import time

        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not configured.")

        # Candidate models for fallback (supporting gemini-3.8-flash and 2.5-flash)
        fallback_chain = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"]
        candidate_models = [self.model_name] + [m for m in fallback_chain if m != self.model_name]
        active_model = self.model_name

        gemini_tools = [
            {
                "function_declarations": self.get_tool_definitions()
            }
        ]

        contents = [
            {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}
        ]

        # Multi-turn tool-calling loop (Max 5 turns)
        for _ in range(5):
            payload = {
                "contents": contents,
                "tools": gemini_tools
            }

            res = None
            last_err = None

            for m in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.gemini_api_key}"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )

                for attempt in range(3):
                    try:
                        with urllib.request.urlopen(req, timeout=30.0) as resp:
                            res = json.loads(resp.read().decode("utf-8"))
                            active_model = m
                            break
                    except urllib.error.HTTPError as e:
                        last_err = e
                        if e.code in (503, 429) and attempt < 2:
                            time.sleep(1.2 * (attempt + 1))
                            continue
                        break
                    except Exception as e:
                        last_err = e
                        break

                if res:
                    break

            if not res:
                err_msg = str(last_err)
                if hasattr(last_err, "read"):
                    try:
                        err_msg = last_err.read().decode("utf-8")
                    except Exception:
                        pass
                raise RuntimeError(f"Gemini API request failed across models: {err_msg}")

            candidate = res.get("candidates", [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            # Check for function calls
            has_func_call = False
            function_calls = []

            for p in parts:
                if "functionCall" in p:
                    has_func_call = True
                    function_calls.append(p["functionCall"])

            # If no function call, this is the final text response!
            if not has_func_call:
                final_text = "".join([p.get("text", "") for p in parts if "text" in p])
                return final_text, tools_log

            # Append model's response (with functionCall) to history
            contents.append(content)

            # Execute tool calls and create tool responses
            function_response_parts = []
            for fc in function_calls:
                fn_name = fc["name"]
                fn_args = fc.get("args", {})

                # Execute local tool
                tool_result = self.execute_tool(fn_name, fn_args)

                # Log tool execution
                tools_log.append({
                    "tool": fn_name,
                    "args": fn_args,
                    "summary": f"{fn_name}({', '.join(f'{k}={v}' for k, v in fn_args.items())})"
                })

                function_response_parts.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": tool_result
                    }
                })

            # Append tool execution results
            contents.append({
                "role": "user",
                "parts": function_response_parts
            })

        return "보고서 생성 중 도구 호출 최대 횟수를 초과했습니다.", tools_log

    # =========================================================================
    # 5. Engine Implementation: Local Ollama (Qwen 2.5)
    # =========================================================================

    def _run_ollama_agent(
        self, system_prompt: str, user_prompt: str, tools_log: List[Dict[str, Any]]
    ) -> (str, List[Dict[str, Any]]):
        """Execute tool calling loop against local Ollama OpenAI-compatible endpoint."""
        url = f"{self.ollama_base_url}/v1/chat/completions"

        # Format tools as OpenAI tools
        openai_tools = [
            {"type": "function", "function": t}
            for t in self.get_tool_definitions()
        ]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        for _ in range(5):
            payload = {
                "model": self.model_name,
                "messages": messages,
                "tools": openai_tools,
                "temperature": 0.2
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            try:
                with urllib.request.urlopen(req) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                raise RuntimeError(f"Ollama local connection error: {e}. Ensure Ollama is running (`ollama run {self.model_name}`).")

            choice = res.get("choices", [{}])[0]
            msg = choice.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            # If no tool calls, return final content
            if not tool_calls:
                return msg.get("content", ""), tools_log

            messages.append(msg)

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"].get("arguments", "{}"))
                except Exception:
                    fn_args = {}

                tool_result = self.execute_tool(fn_name, fn_args)

                tools_log.append({
                    "tool": fn_name,
                    "args": fn_args,
                    "summary": f"{fn_name}({', '.join(f'{k}={v}' for k, v in fn_args.items())})"
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", "call_1"),
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

        return "로컬 모델 도구 호출 루프가 완료되었습니다.", tools_log

    # =========================================================================
    # 6. Engine Implementation: OpenCode (Muse Spark 1.3 / Nemotron / Ling)
    # =========================================================================

    def _run_opencode_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        tools_log: List[Dict[str, Any]],
        target_ticker: str,
        peer_tickers: List[str]
    ) -> (str, List[Dict[str, Any]]):
        """
        Execute OpenCode model (e.g. Muse Spark 1.3 / Nemotron) with pre-fetched database context.
        """
        # 1. Pre-fetch target financial data
        target_fin = self.tool_get_quarterly_financials(target_ticker, limit=4)
        tools_log.append({
            "tool": "get_quarterly_financials",
            "args": {"ticker": target_ticker, "limit": 4},
            "summary": f"get_quarterly_financials(ticker={target_ticker}, limit=4)"
        })

        # 2. Pre-fetch peer financial data
        peer_data = {}
        for p in peer_tickers:
            p_clean = p.strip()
            if p_clean:
                p_fin = self.tool_get_quarterly_financials(p_clean, limit=4)
                peer_data[p_clean] = p_fin
                tools_log.append({
                    "tool": "get_quarterly_financials",
                    "args": {"ticker": p_clean, "limit": 4},
                    "summary": f"get_quarterly_financials(ticker={p_clean}, limit=4)"
                })

        # 3. Pre-fetch transcripts
        trans_res = self.tool_search_transcripts(target_ticker, query="HBM Blackwell CapEx guidance margin")
        tools_log.append({
            "tool": "search_earning_call_transcripts",
            "args": {"ticker": target_ticker, "query": "core topics"},
            "summary": f"search_earning_call_transcripts(ticker={target_ticker}, query='core topics')"
        })

        # 4. Pre-fetch consensus
        cons_res = self.tool_get_consensus_surprise(target_ticker)
        tools_log.append({
            "tool": "get_consensus_surprise",
            "args": {"ticker": target_ticker},
            "summary": f"get_consensus_surprise(ticker={target_ticker})"
        })

        # 5. Pre-fetch lead indicators & GPU rental
        lead_res = self.tool_get_lead_indicators()
        tools_log.append({
            "tool": "get_lead_indicators",
            "args": {},
            "summary": "get_lead_indicators()"
        })
        gpu_res = self.tool_get_gpu_rental_prices("H100")
        tools_log.append({
            "tool": "get_gpu_rental_prices",
            "args": {"gpu_model": "H100"},
            "summary": "get_gpu_rental_prices(gpu_model='H100')"
        })

        # 6. Synthesize rich prompt
        context_block = f"""
[시스템 데이터베이스 실측 팩트 데이터 (반드시 아래 수치만 인용하십시오)]
1. 분석 대상 기업({target_ticker}) 최근 4개 분기 실적 확정치:
{json.dumps(target_fin.get('series', []), ensure_ascii=False, indent=2)}

2. 피어 비교 기업군 실적 확정치:
{json.dumps(peer_data, ensure_ascii=False, indent=2)}

3. 대상 기업 어닝콜 전문 발췌 (경영진 발언 & 애널리스트 질의응답):
{json.dumps(trans_res.get('results', []), ensure_ascii=False, indent=2)}

4. 어닝 서프라이즈(Beat/Miss) 및 실적 발표 후 주가 반응:
{json.dumps(cons_res.get('records', []), ensure_ascii=False, indent=2)}

5. 산업 선행 지표 (메모리 현물가 & 관세청 반도체 수출통계 & GPU 렌탈가):
- 메모리 현물가: {json.dumps(lead_res.get('memory_spot_latest', []), ensure_ascii=False)}
- 관세청 반도체 수출: {json.dumps(lead_res.get('kr_semiconductor_export_latest', []), ensure_ascii=False)}
- H100 GPU 렌탈 스팟가: {json.dumps(gpu_res.get('current_benchmark', {}), ensure_ascii=False)}
"""

        augmented_prompt = f"""{system_prompt}

{context_block}

{user_prompt}
"""

        try:
            cmd = ["opencode", "run", "-m", self.model_name, "--format", "json", augmented_prompt]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            output_parts = []
            for line in proc.stdout.splitlines():
                if line.strip():
                    try:
                        evt = json.loads(line)
                        if evt.get("type") == "text":
                            txt = evt.get("part", {}).get("text", "")
                            if txt:
                                output_parts.append(txt)
                    except Exception:
                        pass

            report_text = "".join(output_parts).strip()
            if not report_text:
                report_text = proc.stdout.strip()

            if not report_text:
                report_text = f"## OpenCode ({self.model_name}) 실행 결과\n\n모델 실행 중 출력이 비어 있습니다. (stderr: {proc.stderr[:300]})"

            return report_text, tools_log
        except Exception as e:
            return f"OpenCode 실행 오류 ({self.model_name}): {str(e)}", tools_log

    # =========================================================================
    # 7. Status Checker
    # =========================================================================

    @staticmethod
    def check_engine_status() -> Dict[str, Any]:
        """Check availability of Gemini API, local Ollama, and OpenCode server."""
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        gemini_ok = bool(gemini_key and gemini_key.startswith("AIzaSy"))

        # Test Ollama reachability
        ollama_ok = False
        ollama_models = []
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ollama_ok = True
                ollama_models = [m.get("name") for m in data.get("models", [])]
        except Exception:
            ollama_ok = False

        # Test OpenCode CLI
        opencode_ok = bool(shutil.which("opencode"))
        opencode_models = [
            "opencode/muse-spark-1.3-contributor-free",
            "opencode/muse-spark-1.2-contributor-free",
            "opencode/nemotron-3.5-lightning-free",
            "opencode/ling-3.0-flash-fin-free"
        ] if opencode_ok else []

        return {
            "gemini": {
                "available": gemini_ok,
                "models": ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-2.5-pro"],
                "model_default": "gemini-2.5-flash",
                "message": "Gemini API 키 사용 가능 (2.5 Flash & 3.8 Flash)" if gemini_ok else "GEMINI_API_KEY 미설정"
            },
            "opencode": {
                "available": opencode_ok,
                "models": opencode_models,
                "model_default": "opencode/muse-spark-1.3-contributor-free",
                "message": "OpenCode CLI 사용 가능 (Muse Spark 1.3 탑재)" if opencode_ok else "OpenCode 미설치"
            },
            "ollama": {
                "available": ollama_ok,
                "models": ollama_models,
                "model_default": "qwen2.5:7b",
                "message": "로컬 Ollama 온라인" if ollama_ok else "Ollama 오프라인 (터미널에서 ollama serve 필요)"
            }
        }
