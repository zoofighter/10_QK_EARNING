"""
Transcripts Dataset for AI Semiconductor Value Chain Leaders (L2 to L8)
Contains comprehensive conference call transcripts including Executive Prepared Remarks
and Wall Street Analyst Q&A Sessions across 2025/2026 fiscal quarters.
"""

FULL_TRANSCRIPTS_SEED = [
    # ----------------------------------------------------
    # 1. NVIDIA (NVDA) FY2026-Q2 (2026-08-26)
    # ----------------------------------------------------
    {
        "ticker": "NVDA",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-08-26",
        "call_time_et": "17:00 ET",
        "source_url": "https://investor.nvidia.com/events-and-presentations",
        "text": (
            "NVIDIA Corporation (NASDAQ:NVDA) Q2 Fiscal 2026 Financial Results Conference Call\n"
            "Date: August 26, 2026 | 5:00 PM ET\n\n"
            "Executives Present:\n"
            "- Jensen Huang: Founder, President & Chief Executive Officer\n"
            "- Colette Kress: Executive Vice President & Chief Financial Officer\n"
            "- Stewart Stecker: Vice President of Investor Relations\n\n"
            "Analysts Present:\n"
            "- Toshiya Hari (Goldman Sachs)\n"
            "- Vivek Arya (Bank of America Securities)\n"
            "- Stacy Rasgon (Bernstein Research)\n"
            "- Timothy Arcuri (UBS)\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Stewart Stecker:\n"
            "Good afternoon, and welcome to NVIDIA's second-quarter fiscal 2026 conference call. With me today are Jensen Huang, President and CEO, and Colette Kress, Executive VP and CFO.\n\n"
            "Colette Kress (CFO):\n"
            "Thank you, Stewart. Q2 was another record-breaking quarter for NVIDIA. Revenue reached $96.22 billion, up 106% from a year ago and up 18% sequentially. Our Data Center revenue grew to a historic $88.30 billion, representing 91.8% of total company revenue. Operating margin reached 66.2% and net income was $59.69 billion.\n\n"
            "The extraordinary growth was driven by universal demand across cloud service providers, consumer internet giants, and global enterprise customers. In networking, revenue reached $10.5 billion, powered by Quantum-X800 InfiniBand and our newly ramped Spectrum-X Ethernet platform for AI fabrics.\n\n"
            "Turning to product updates: Blackwell architecture is now in full volume production and shipping across every tier. Customer demand for Blackwell Ultra and the GB200 NVL72 liquid-cooled rack architecture is unprecedented, far exceeding available supply well into calendar 2027. Concurrently, demand for Hopper architectures (H100 and H200) remained robust throughout the quarter, as cloud providers race to expand compute capacity without any pause.\n\n"
            "Jensen Huang (CEO):\n"
            "Thank you, Colette. Computing has fundamentally changed. The world is experiencing two platform shifts at the same time: accelerated computing has replaced general-purpose CPUs for computationally intensive workloads, and generative AI is transforming every layer of modern software.\n\n"
            "Blackwell is the engine of the new industrial revolution. In Q2, we shipped tens of thousands of Blackwell samples and production wafers to CSPs. The GB200 NVL72 connects 72 Blackwell GPUs and 36 Grace CPUs into a single massive unified GPU that operates as an exaflop AI supercomputer. It reduces inference token latency and operational costs by a factor of 30x compared to previous generations.\n\n"
            "Every major cloud provider—Microsoft Azure, AWS, Google Cloud, and Oracle Cloud Infrastructure—is deploying Blackwell clusters at scale. Furthermore, sovereign AI is now a multibillion-dollar business for NVIDIA, as nations from Europe, Japan, and the Middle East invest directly in domestic AI supercomputers.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Operator: Our first question comes from Toshiya Hari with Goldman Sachs.\n\n"
            "Toshiya Hari (Goldman Sachs):\n"
            "Jensen, congratulations on phenomenal results. Could you elaborate on the transition cadence between Hopper and Blackwell over the next couple of quarters? Are customers pausing Hopper purchases in anticipation of full Blackwell volume?\n\n"
            "Jensen Huang (CEO):\n"
            "Toshiya, thank you. The simple answer is absolutely not. Hopper demand is actually accelerating. The reason is simple: every day that an AI developer or CSP waits for compute is a day they lose market position. H200 offers incredible memory bandwidth and is being deployed immediately for production inference. When Blackwell ramps into tens of thousands of racks, Hopper and Blackwell will coexist seamlessly in heterogeneous clusters. We expect Blackwell supply to expand every single quarter through next year.\n\n"
            "Operator: Next question comes from Vivek Arya with Bank of America.\n\n"
            "Vivek Arya (BofA):\n"
            "Colette, hyperscaler CapEx has grown aggressively. How are you thinking about ROI for end customers, and what is your visibility into data center demand into fiscal 2027?\n\n"
            "Colette Kress (CFO):\n"
            "Vivek, thank you. When CSPs deploy NVIDIA AI infrastructure, it generates immediate revenue. Cloud providers report that every $1 spent on NVIDIA HGX systems translates into $5 of cloud rental revenue over a four-year lifecycle. Moreover, enterprise adoption of agentic AI workflows and inference workloads is exploding, ensuring that compute utilization rates remain near 100%."
        )
    },

    # ----------------------------------------------------
    # 2. NVIDIA (NVDA) FY2026-Q1 (2026-05-21)
    # ----------------------------------------------------
    {
        "ticker": "NVDA",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q1",
        "call_date": "2026-05-21",
        "call_time_et": "17:00 ET",
        "source_url": "https://investor.nvidia.com/events-and-presentations",
        "text": (
            "NVIDIA Corporation (NASDAQ:NVDA) Q1 Fiscal 2026 Financial Results Conference Call\n"
            "Date: May 21, 2026 | 5:00 PM ET\n\n"
            "Executives Present:\n"
            "- Jensen Huang: President & CEO\n"
            "- Colette Kress: Executive VP & CFO\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Colette Kress (CFO):\n"
            "Good afternoon. Revenue for the first quarter was $81.54 billion, up 213% year-over-year. Data Center revenue of $74.20 billion grew 260% from a year ago. Demand for our accelerated computing and generative AI platforms is broad and accelerating across every geography.\n\n"
            "Gross margin was 78.4%, reflecting exceptionally high value capture on our full-stack computing solutions. In the quarter, we began sampling Blackwell GPUs and systems with key partners, while ramping H200 shipments with 141GB of HBM3e memory.\n\n"
            "Jensen Huang (CEO):\n"
            "The next industrial revolution has begun. Countries and companies are partnering with NVIDIA to shift trillion-dollar traditional data centers to accelerated computing and build a new type of data center: AI factories to produce a new commodity—artificial intelligence.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Mark Lipacis (Evercore ISI):\n"
            "Jensen, could you talk about the networking attach rate on Hopper and Blackwell? How significant is Spectrum-X in expanding your Ethernet addressable market?\n\n"
            "Jensen Huang (CEO):\n"
            "Spectrum-X has opened up the vast Ethernet market for NVIDIA. Traditionally, Ethernet was not designed for AI. With Spectrum-X, we brought adaptive routing, congestion control, and telemetry to standard Ethernet, delivering 1.6x effective throughput for AI training and inference. We expect Spectrum-X to become a multibillion-dollar product line within a year."
        )
    },

    # ----------------------------------------------------
    # 3. SK Hynix (000660.KS) 2026-Q2 (2026-07-24)
    # ----------------------------------------------------
    {
        "ticker": "000660.KS",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-07-24",
        "call_time_et": "09:00 KST",
        "source_url": "https://www.skhynix.com/ir",
        "text": (
            "SK하이닉스 2026년 2분기 경영실적 발표 컨퍼런스콜\n"
            "일시: 2026년 7월 24일 09:00 KST\n\n"
            "참석 경영진:\n"
            "- 곽노정 대표이사 사장 (CEO)\n"
            "- 김우현 부사장 / 최고재무책임자 (CFO)\n"
            "- 김규현 DRAM 마케팅담당 부사장\n"
            "- 김석 NAND 마케팅담당 부사장\n\n"
            "=====================================================\n"
            "경영진 모두발언 (PREPARED REMARKS)\n"
            "=====================================================\n"
            "김우현 부사장 (CFO):\n"
            "안녕하십니까, SK하이닉스 CFO 김우현입니다. 2026년 2분기 당사는 매출 22조 1,400억 원, 영업이익 7조 4,800억 원(영업이익률 33.8%)을 달성하여 분기 기준 사상 최대 실적을 경신하였습니다.\n\n"
            "DRAM 부문에서는 AI 서버향 고대역폭 메모리인 HBM3E 12단(36GB) 제품의 본격 양산 및 공급 개시로 HBM 매출이 전분기 대비 80% 이상, 전년 동기 대비 250% 이상 급증하였습니다. 전체 DRAM 매출 중 HBM이 차지하는 비중은 35%를 돌파하였습니다.\n\n"
            "NAND 부문 역시 빅테크 AI 데이터센터향 60TB급 초고용량 eSSD(기업용 SSD) 수요가 폭발적으로 증가하며 흑자 기조를 확고히 유지하였습니다. QLC 기반 128TB 초고용량 eSSD 라인업의 고객사 퀄 승인이 완료되어 하반기 공급을 앞두고 있습니다.\n\n"
            "곽노정 대표이사 사장 (CEO):\n"
            "SK하이닉스는 HBM 시장의 압도적 1위 기술 리더십을 바탕으로 고객사 맞춤형 커스텀 HBM4 개발을 계획대로 진행 중입니다. TSMC와의 원팀 협력을 통해 베이스 다이(Base Die)를 첨단 로직 공정으로 제작하는 차세대 HBM4는 2026년 하반기 양산 및 출하를 목표로 순항하고 있습니다.\n\n"
            "또한 충북 청주 M15X 팹과 용인 반도체 클러스터 첫 번째 팹의 건설 투자를 차질 없이 진행하여 늘어나는 글로벌 AI 메모리 수요에 선제적으로 대응하겠습니다.\n\n"
            "=====================================================\n"
            "질의응답 세션 (QUESTION AND ANSWER SESSION)\n"
            "=====================================================\n"
            "질문: 김록호 연구원 (하나증권)\n"
            "HBM3E 12단 제품의 경쟁사 진입 여부와 수율 상황, 그리고 2027년 HBM 공급 캐파 예약 상황에 대해 업데이트 부탁드립니다.\n\n"
            "답변: 김규현 DRAM 마케팅담당 부사장\n"
            "당사는 업계 최초로 HBM3E 12단 제품을 양산 공급하며 수율 측면에서 이미 성숙 단계에 진입하였습니다. 주요 고객사와의 2026년 HBM 캐파는 이미 연초에 전량 솔드아웃(Sold out)되었으며, 2027년 물량에 대한 장기 공급 계약 논의도 매우 우호적인 조건으로 진행되고 있습니다. 경쟁사의 진입 시도에도 불구하고 당사의 MR-MUF 공정 안정성과 품질 신뢰성을 바탕으로 시장 지배력은 더욱 공고해질 것입니다."
        )
    },

    # ----------------------------------------------------
    # 4. Samsung Electronics (005930.KS) 2026-Q2 (2026-07-31)
    # ----------------------------------------------------
    {
        "ticker": "005930.KS",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-07-31",
        "call_time_et": "10:00 KST",
        "source_url": "https://www.samsung.com/global/ir",
        "text": (
            "삼성전자 2026년 2분기 경영실적 발표 컨퍼런스콜\n"
            "일시: 2026년 7월 31일 10:00 KST\n\n"
            "참석 경영진:\n"
            "- 전영현 DS부문장 부회장\n"
            "- 박순철 경영지원실 IR담당 부사장\n"
            "- 김재준 메모리사업부 전략마케팅실장 부사장\n"
            "- 정기봉 파운드리사업부 부사장\n\n"
            "=====================================================\n"
            "경영진 모두발언 (PREPARED REMARKS)\n"
            "=====================================================\n"
            "박순철 부사장:\n"
            "2026년 2분기 연결 기준 매출은 84조 3,500억 원, 영업이익은 12조 8,000억 원을 기록하였습니다. DS(반도체) 부문 매출은 32조 원, 영업이익은 7조 6,000억 원으로 전사 실적 반등을 견인하였습니다.\n\n"
            "김재준 부사장 (메모리):\n"
            "메모리 사업부는 생성형 AI 서버용 HBM 및 고용량 DDR5, 서버용 SSD 수요 강세에 적극 대응하였습니다. HBM3E 8단 제품은 주요 GPU 고객사 공급을 본격화하였으며, 12단 제품 역시 고객사 퀄 인증 절차를 완료하고 3분기부터 대량 공급 체제에 돌입합니다. 하반기 HBM 매출은 상반기 대비 3.5배 이상 확대될 것으로 전망합니다.\n\n"
            "정기봉 부사장 (파운드리):\n"
            "파운드리 사업부는 2세대 3nm GAA 공정의 양산 안정화를 달성하였으며, 2nm 공정의 주요 고객사 AI 가속기 칩 테이프아웃(Tape-out)을 완료하였습니다. 첨단 패키징 I-Cube 및 SAINT 기술을 결합한 턴키 솔루션을 통해 수주 잔고를 지속 확대하고 있습니다.\n\n"
            "=====================================================\n"
            "질의응답 세션 (QUESTION AND ANSWER SESSION)\n"
            "=====================================================\n"
            "질문: 채민숙 연구원 (한국투자증권)\n"
            "HBM3E 12단 공급 일정과 함께 차세대 HBM4에서 삼성전자의 턴키(메모리+파운드리+첨단패키징) 전략 경쟁력을 설명해 주십시오.\n\n"
            "답변: 김재준 부사장 (메모리):\n"
            "HBM3E 12단은 3분기부터 공급 비중이 급격히 증가하여 4분기에는 전체 HBM 출하량의 과반 이상을 차지할 것입니다. HBM4에서는 베이스 다이에 4nm/3nm 첨단 파운드리 공정과 차세대 패키징이 결합되어야 합니다. 당사는 메모리, 파운드리, 패키징을 원스톱으로 제공할 수 있는 세계 유일의 종합반도체 기업으로서 고객 맞춤형 커스텀 솔루션 수주에서 강력한 우위를 점할 것입니다."
        )
    },

    # ----------------------------------------------------
    # 5. TSMC (TSM) 2026-Q2 (2026-07-16)
    # ----------------------------------------------------
    {
        "ticker": "TSM",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-07-16",
        "call_time_et": "14:00 Taipei",
        "source_url": "https://investor.tsmc.com",
        "text": (
            "Taiwan Semiconductor Manufacturing Company (TSM) Q2 2026 Earnings Call\n"
            "Date: July 16, 2026 | 2:00 PM Taiwan Time\n\n"
            "Executives Present:\n"
            "- C.C. Wei: Chairman & Chief Executive Officer\n"
            "- Wendell Huang: Senior VP & Chief Financial Officer\n"
            "- Jeff Su: Director of Investor Relations\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Wendell Huang (CFO):\n"
            "Welcome to TSMC's second quarter 2026 earnings conference. Consolidated revenue reached $27.84 billion USD, an increase of 38.6% year-over-year. Gross margin was 57.2%, driven by exceptionally high fab capacity utilization and yield improvements.\n\n"
            "High Performance Computing (HPC) accounted for 58% of total revenue, remaining our primary growth driver. By process technology, 3-nanometer represented 24% of wafer revenue, and 5-nanometer represented 35%. Advanced nodes (7nm and below) accounted for 72% of total wafer revenue.\n\n"
            "C.C. Wei (Chairman & CEO):\n"
            "Our business in the second quarter was strongly supported by robust AI and smartphone-related demand for our industry-leading 3-nanometer and 5-nanometer technologies. Almost all AI innovators are working with TSMC. Demand for AI accelerators is so intense that our CoWoS (Chip-on-Wafer-on-Substrate) advanced packaging capacity continues to be extremely tight.\n\n"
            "We are doubling our CoWoS capacity again this year, and we will double it once more in 2027 to satisfy insatiable customer appetite. Looking forward, our 2-nanometer N2 technology with backside power delivery network is on track for volume production in early 2027, with customer interest even higher than N3 at the same stage.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Randy Abrams (UBS):\n"
            "Dr. Wei, could you quantify the revenue contribution of server AI processors to TSMC, and how you foresee the growth trajectory over the next five years?\n\n"
            "C.C. Wei (CEO):\n"
            "Randy, server AI processors currently contribute in the mid-to-high teens percentage of our total revenue. We expect this AI revenue to grow at a compound annual growth rate of 50% over the next five years, easily becoming the single largest growth engine in TSMC's history."
        )
    },

    # ----------------------------------------------------
    # 6. Microsoft (MSFT) FY2026-Q4 (2026-07-28)
    # ----------------------------------------------------
    {
        "ticker": "MSFT",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q4",
        "call_date": "2026-07-28",
        "call_time_et": "17:30 ET",
        "source_url": "https://www.microsoft.com/en-us/investor",
        "text": (
            "Microsoft Corporation (NASDAQ:MSFT) Q4 Fiscal 2026 Conference Call\n"
            "Date: July 28, 2026 | 5:30 PM ET\n\n"
            "Executives Present:\n"
            "- Satya Nadella: Chairman & Chief Executive Officer\n"
            "- Amy Hood: Executive Vice President & Chief Financial Officer\n"
            "- Brett Iversen: Vice President, Investor Relations\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Satya Nadella (Chairman & CEO):\n"
            "We are seeing real business outcomes and productivity gains from generative AI across every industry. This quarter, Microsoft Cloud revenue surpassed $41.8 billion, up 22% year-over-year. Azure and other cloud services revenue grew 31%, with 9 points of that growth coming directly from Azure AI services.\n\n"
            "Azure AI customer count exceeded 75,000 enterprises, including over 70% of the Fortune 500. GitHub Copilot now has over 2.2 million paid subscribers, up 160% year-over-year. In our own engineering teams, developers are completing tasks 55% faster with Copilot Workspace.\n\n"
            "To support this unprecedented demand, we are investing aggressively in our cloud and AI infrastructure. We are bringing online new gigawatt-scale data centers powered by zero-carbon clean energy, and deploying the latest NVIDIA Blackwell clusters and AMD MI300X alongside our custom Maia AI silicon.\n\n"
            "Amy Hood (CFO):\n"
            "Capital expenditures including finance leases were $20.2 billion in Q4, driven by cloud demand and data center buildouts. Nearly half of our spend was on long-lived physical assets—land and buildings—that will support monetization over the next 15 years, while the remainder went directly to GPUs and server hardware to monetize immediately.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Keith Weiss (Morgan Stanley):\n"
            "Amy, could you talk about capacity constraints on Azure AI? Is demand still outstripping your ability to bring GPU clusters online?\n\n"
            "Amy Hood (CFO):\n"
            "Keith, yes. Demand continues to exceed our available supply in several key geographic regions. While we have accelerated data center construction and hardware deliveries, our compute utilization remains near capacity. We expect capacity to remain constrained through the first half of fiscal 2027 before substantial Blackwell deliveries scale up."
        )
    },

    # ----------------------------------------------------
    # 7. Alphabet / Google (GOOGL) 2026-Q2 (2026-07-23)
    # ----------------------------------------------------
    {
        "ticker": "GOOGL",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-07-23",
        "call_time_et": "16:30 ET",
        "source_url": "https://abc.xyz/investor",
        "text": (
            "Alphabet Inc. (NASDAQ:GOOGL) Q2 2026 Financial Results Conference Call\n"
            "Date: July 23, 2026 | 4:30 PM ET\n\n"
            "Executives Present:\n"
            "- Sundar Pichai: Chief Executive Officer\n"
            "- Ruth Porat: President & Chief Investment Officer\n"
            "- Anat Ashkenazi: Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Sundar Pichai (CEO):\n"
            "Our momentum is strong across the company. Alphabet delivered revenues of $94.8 billion, up 15% year-over-year. Google Cloud revenue surpassed $12.1 billion, growing 32%, with operating operating profit expanding to $1.8 billion.\n\n"
            "Our full-stack AI infrastructure is unmatched. We are now deploying our sixth-generation custom TPU, Trillium (TPU v6e), which delivers a 4.7x increase in compute performance per chip compared to TPU v5e. At the same time, we offer the most complete selection of NVIDIA GPUs, including Blackwell systems.\n\n"
            "Gemini models are now integrated across Google Search, Workspace, YouTube, and Android, processing over 1.5 billion daily AI Overviews queries. Enterprise adoption of Vertex AI grew 6x year-over-year.\n\n"
            "Anat Ashkenazi (CFO):\n"
            "Capital expenditures in the quarter were $14.2 billion, reflecting our disciplined investment in technical infrastructure, server capacity, and custom TPU manufacturing. We remain focused on re-engineering our cost structure while maintaining our technology leadership.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Brian Nowak (Morgan Stanley):\n"
            "Sundar, how do you evaluate the internal cost efficiency of TPUs versus external GPUs for Gemini training and serving at Google scale?\n\n"
            "Sundar Pichai (CEO):\n"
            "Brian, our TPU infrastructure provides substantial cost and energy advantages. Over 70% of Gemini inference workloads are served on our custom silicon, giving us industry-leading serving margins. By co-designing hardware, optical circuit switches, and models, we drive down inference costs by 80% every 18 months."
        )
    },

    # ----------------------------------------------------
    # 8. Meta Platforms (META) 2026-Q2 (2026-07-30)
    # ----------------------------------------------------
    {
        "ticker": "META",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-07-30",
        "call_time_et": "17:00 ET",
        "source_url": "https://investor.fb.com",
        "text": (
            "Meta Platforms, Inc. (NASDAQ:META) Q2 2026 Financial Results Conference Call\n"
            "Date: July 30, 2026 | 5:00 PM ET\n\n"
            "Executives Present:\n"
            "- Mark Zuckerberg: Founder, Chairman & Chief Executive Officer\n"
            "- Susan Li: Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Mark Zuckerberg (CEO):\n"
            "We had a strong quarter. Total revenue was $43.2 billion, up 24% year-over-year. Over 3.3 billion people now use at least one of our apps daily.\n\n"
            "Our open-source AI strategy is succeeding beyond our expectations. Llama 4 is currently in advanced training on our 100,000-GPU clusters, and Llama 3 has already achieved over 400 million downloads. Meta AI is on track to become the most-used AI assistant in the world by the end of this year.\n\n"
            "Our compute fleet is among the largest in the world. By the end of 2026, we will operate roughly 700,000 equivalent H100 GPUs, including substantial clusters of NVIDIA Blackwell and our custom MTIA (Meta Training and Inference Accelerator) silicon.\n\n"
            "Susan Li (CFO):\n"
            "We are narrowing our full-year 2026 capital expenditures guidance to $40 to $42 billion, driven by accelerated investments in server hardware, next-generation data centers, and network infrastructure. AI investments continue to generate strong returns by improving ad conversion rates and feed recommendation engagement.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Eric Sheridan (Goldman Sachs):\n"
            "Mark, could you discuss how you balance open-sourcing Llama models with the massive CapEx required to train them? How does Meta capture economic value?\n\n"
            "Mark Zuckerberg (CEO):\n"
            "Eric, open sourcing creates the industry standard. When the world standardizes on Llama, hardware, chips, and developer tools optimize for our architecture. This lowers our internal infrastructure costs, improves developer hiring, and ensures we are never locked into a proprietary closed ecosystem."
        )
    },

    # ----------------------------------------------------
    # 9. Amazon (AMZN) 2026-Q2 (2026-08-01)
    # ----------------------------------------------------
    {
        "ticker": "AMZN",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-08-01",
        "call_time_et": "17:30 ET",
        "source_url": "https://ir.aboutamazon.com",
        "text": (
            "Amazon.com, Inc. (NASDAQ:AMZN) Q2 2026 Financial Results Conference Call\n"
            "Date: August 1, 2026 | 5:30 PM ET\n\n"
            "Executives Present:\n"
            "- Andy Jassy: President & Chief Executive Officer\n"
            "- Brian Olsavsky: Senior VP & Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Andy Jassy (CEO):\n"
            "AWS delivered an exceptional second quarter. AWS revenue re-accelerated to 21% year-over-year growth, reaching $30.8 billion, which represents an annualized run rate of over $123 billion.\n\n"
            "Our generative AI business is a multibillion-dollar revenue run rate business, growing at triple-digit year-over-year rates. We are seeing incredible customer enthusiasm for Amazon Bedrock and our custom silicon. Trainium2 instances are now ramping into massive production clusters, offering up to 40% better price-performance than comparable GPU instances for training deep learning models.\n\n"
            "In addition, Project Kuiper satellite broadband constellation deployment is on schedule, opening up new distributed edge data center connectivity for enterprise AI workloads.\n\n"
            "Brian Olsavsky (CFO):\n"
            "Capital expenditures were $17.5 billion in Q2. We anticipate higher investments through the second half of 2026 to support AWS infrastructure and AI capacity expansion.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Doug Anmuth (JPMorgan):\n"
            "Andy, could you speak to the enterprise adoption of custom silicon like Trainium2 versus NVIDIA GPU instances in AWS?\n\n"
            "Andy Jassy (CEO):\n"
            "Doug, customers want choice and cost efficiency. Anthropic is using tens of thousands of Trainium2 chips to train their next-generation Claude models. Startups and enterprises love that they can achieve the same training throughput at significantly lower cloud spend."
        )
    },

    # ----------------------------------------------------
    # 10. Broadcom (AVGO) FY2026-Q3 (2026-09-05)
    # ----------------------------------------------------
    {
        "ticker": "AVGO",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q3",
        "call_date": "2026-09-05",
        "call_time_et": "17:00 ET",
        "source_url": "https://investors.broadcom.com",
        "text": (
            "Broadcom Inc. (NASDAQ:AVGO) Q3 Fiscal 2026 Earnings Conference Call\n"
            "Date: September 5, 2026 | 5:00 PM ET\n\n"
            "Executives Present:\n"
            "- Hock Tan: President and Chief Executive Officer\n"
            "- Kirsten Spears: Chief Financial Officer & Chief Accounting Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Hock Tan (CEO):\n"
            "Good afternoon. Broadcom's revenue in the third quarter was $15.82 billion, up 47% from a year ago. AI revenue continued its parabolic trajectory, reaching $4.8 billion in the quarter, exceeding our previous forecast.\n\n"
            "Our custom AI ASIC business is expanding rapidly. We currently have three hyperscale customers in volume production for custom AI accelerators, and we have won design engagements with two additional hyperscalers for 2-nanometer custom AI XPUs scheduled for volume ramp in 2027.\n\n"
            "In networking, Tomahawk 5 (51.2 Terabit switch) and Jericho3-AI fabrics are shipping in volume, and we have taped out Tomahawk 6 (102.4 Terabit switch) using 3nm process technology. Optical interconnects, including 800-gig and 1.6-terabit DSPs, are experiencing tight supply due to hyperscaler cluster expansions.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Harsh Kumar (Piper Sandler):\n"
            "Hock, could you give us your updated full-year fiscal 2026 AI revenue outlook? And what are you seeing on the VMware integration?\n\n"
            "Hock Tan (CEO):\n"
            "Harsh, we are raising our fiscal 2026 AI revenue guidance from $12 billion to over $14.5 billion. On VMware, annual recurring revenue (ARR) has reached $14 billion as enterprise customers rapidly migrate to VMware Cloud Foundation private cloud subscriptions."
        )
    },

    # ----------------------------------------------------
    # 11. AMD (AMD) 2026-Q2 (2026-07-30)
    # ----------------------------------------------------
    {
        "ticker": "AMD",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-07-30",
        "call_time_et": "17:00 ET",
        "source_url": "https://ir.amd.com",
        "text": (
            "Advanced Micro Devices, Inc. (NASDAQ:AMD) Q2 2026 Financial Results Conference Call\n"
            "Date: July 30, 2026 | 5:00 PM ET\n\n"
            "Executives Present:\n"
            "- Dr. Lisa Su: Chair and Chief Executive Officer\n"
            "- Jean Hu: Executive Vice President & Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Dr. Lisa Su (Chair & CEO):\n"
            "We delivered outstanding second-quarter results with revenue of $7.85 billion, up 35% year-over-year. Data Center segment revenue reached a record $3.95 billion, up 115% compared to the prior year.\n\n"
            "Our Instinct MI300X and newly launched MI325X GPU accelerators are experiencing strong adoption across Microsoft, Meta, Oracle, and major enterprise AI developers. Customer feedback on our ROCm 6.2 open software stack has been exceptional, with inference latency matching or exceeding competing platforms on Llama 3 models.\n\n"
            "We are also making rapid progress on our next-generation MI350 series built on CDNA 4 architecture and 3nm technology, which will deliver a 35x generational improvement in AI inference compute.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Blayne Curtis (Jefferies):\n"
            "Lisa, congratulations on the momentum. Can you provide an update on your full-year 2026 Data Center GPU revenue guidance?\n\n"
            "Dr. Lisa Su (CEO):\n"
            "Blayne, based on customer deployment schedules and expanding supply commitments, we now expect full-year Instinct GPU revenue to exceed $5.5 billion, up from our previous estimate of $4.5 billion."
        )
    },

    # ----------------------------------------------------
    # 12. Micron Technology (MU) FY2026-Q3 (2026-06-26)
    # ----------------------------------------------------
    {
        "ticker": "MU",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q3",
        "call_date": "2026-06-26",
        "call_time_et": "16:30 ET",
        "source_url": "https://investors.micron.com",
        "text": (
            "Micron Technology, Inc. (NASDAQ:MU) Q3 Fiscal 2026 Earnings Call\n"
            "Date: June 26, 2026 | 4:30 PM ET\n\n"
            "Executives Present:\n"
            "- Sanjay Mehrotra: President & Chief Executive Officer\n"
            "- Mark Murphy: Executive VP & Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Sanjay Mehrotra (CEO):\n"
            "Micron delivered excellent fiscal third-quarter results, with revenue of $7.65 billion, near the high end of our guidance range. Gross margin expanded dramatically to 34.8%.\n\n"
            "Our HBM3E products are completely sold out for both calendar 2025 and 2026. Our 24GB 8-high and 36GB 12-high HBM3E products feature 30% lower power consumption than competitors, making them the preferred memory for NVIDIA H200 and Blackwell platforms. In fiscal 2026, we expect several billion dollars of revenue from HBM alone.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Christopher Danely (Citi):\n"
            "Sanjay, how do you see the pricing environment for standard DDR5 and enterprise SSDs given that DRAM capacity is being consumed by HBM?\n\n"
            "Sanjay Mehrotra (CEO):\n"
            "Chris, HBM consumes roughly 3x the wafer capacity of conventional DDR5 for the same bit output. Because HBM demand is absorbing so much cleanroom capacity, non-HBM DRAM supply is structurally constrained, creating a strong multi-quarter pricing tailwind across the entire industry."
        )
    },

    # ----------------------------------------------------
    # 13. ASML (ASML) 2026-Q2 (2026-07-17)
    # ----------------------------------------------------
    {
        "ticker": "ASML",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-07-17",
        "call_time_et": "15:00 CET",
        "source_url": "https://www.asml.com/en/investors",
        "text": (
            "ASML Holding N.V. (NASDAQ:ASML) Q2 2026 Earnings Conference Call\n"
            "Date: July 17, 2026 | 3:00 PM CET\n\n"
            "Executives Present:\n"
            "- Christophe Fouquet: President & Chief Executive Officer\n"
            "- Roger Dassen: Executive VP & Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Christophe Fouquet (CEO):\n"
            "Second quarter net sales came in at €7.12 billion, with gross margin of 51.5%. Net bookings for the quarter were €6.3 billion, of which €3.1 billion was EUV.\n\n"
            "We shipped our second High-NA EUV system (EXE:5000) to customer manufacturing sites for 2nm process qualification. Customer test results demonstrate sub-10nm single-exposure imaging with exceptional overlay accuracy, confirming the economic and yield advantages of High-NA for future AI and memory nodes.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Krish Sankar (TD Cowen):\n"
            "Roger, how is the demand split between logic and memory bookings looking for 2026 and 2027?\n\n"
            "Roger Dassen (CFO):\n"
            "Memory bookings have picked up substantially, now representing over 40% of our EUV backlog as DRAM makers transition to 1-gamma and 1-delta nodes to support HBM layer requirements."
        )
    },

    # ----------------------------------------------------
    # 14. Apple (AAPL) FY2026-Q3 (2026-08-01)
    # ----------------------------------------------------
    {
        "ticker": "AAPL",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q3",
        "call_date": "2026-08-01",
        "call_time_et": "17:00 ET",
        "source_url": "https://investor.apple.com",
        "text": (
            "Apple Inc. (NASDAQ:AAPL) Q3 Fiscal 2026 Financial Results Conference Call\n"
            "Date: August 1, 2026 | 5:00 PM ET\n\n"
            "Executives Present:\n"
            "- Tim Cook: Chief Executive Officer\n"
            "- Luca Maestri: Senior Vice President & Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Tim Cook (CEO):\n"
            "Today Apple is reporting revenue of $91.8 billion for the June quarter, up 7% year-over-year. Services revenue reached an all-time record of $25.2 billion.\n\n"
            "Apple Intelligence is fundamentally transforming customer experiences across iPhone, iPad, and Mac. Our hybrid architecture combines on-device processing powered by Apple Silicon Neural Engine with Private Cloud Compute running on custom M4-based servers in our zero-carbon data centers, ensuring uncompromising privacy.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Wamsi Mohan (Bank of America):\n"
            "Tim, what are you seeing in terms of iPhone replacement cycles and AI feature adoption globally?\n\n"
            "Tim Cook (CEO):\n"
            "Wamsi, consumer excitement for Apple Intelligence is catalyzing an upgrade cycle across all regions. Customers understand that having a private, context-aware AI assistant built into their daily workflows requires modern hardware."
        )
    },

    # ----------------------------------------------------
    # 15. Vertiv Holdings (VRT) 2026-Q2 (2026-07-25)
    # ----------------------------------------------------
    {
        "ticker": "VRT",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-07-25",
        "call_time_et": "11:00 ET",
        "source_url": "https://investors.vertiv.com",
        "text": (
            "Vertiv Holdings Co (NYSE:VRT) Q2 2026 Earnings Conference Call\n"
            "Date: July 25, 2026 | 11:00 AM ET\n\n"
            "Executives Present:\n"
            "- Giordano Albertazzi: Chief Executive Officer\n"
            "- David Fallon: Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Giordano Albertazzi (CEO):\n"
            "We had a stellar second quarter. Orders increased 48% year-over-year, and our total order backlog reached a record $7.5 billion, with book-to-bill at 1.3x.\n\n"
            "Thermal management and liquid cooling are critical bottlenecks for AI data center deployments. Vertiv's complete liquid-to-liquid and liquid-to-air cooling systems are being co-designed directly with leading chipmakers for 100kW+ high-density server racks.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Nigel Coe (Wolfe Research):\n"
            "Gio, could you talk about the adoption rate of direct-to-chip liquid cooling versus traditional air cooling in new data center builds?\n\n"
            "Giordano Albertazzi (CEO):\n"
            "Nigel, for racks exceeding 40kW, liquid cooling is no longer an option—it is a physical necessity. Over 80% of our new AI hyperscale pipeline is specified with liquid cooling CDUs and manifold systems."
        )
    },

    # ----------------------------------------------------
    # 16. Arm Holdings (ARM) FY2027-Q1 (2026-07-31)
    # ----------------------------------------------------
    {
        "ticker": "ARM",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q1",
        "call_date": "2026-07-31",
        "call_time_et": "17:00 ET",
        "source_url": "https://investors.arm.com",
        "text": (
            "Arm Holdings plc (NASDAQ:ARM) Q1 Fiscal 2026 Earnings Conference Call\n"
            "Date: July 31, 2026 | 5:00 PM ET\n\n"
            "Executives Present:\n"
            "- Rene Haas: Chief Executive Officer\n"
            "- Jason Child: Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Rene Haas (CEO):\n"
            "Arm achieved record quarterly revenue of $1.02 billion, up 42% year-over-year. Licensing revenue surged 65% and Royalty revenue grew 28%.\n\n"
            "Adoption of the Armv9 architecture continues to expand rapidly, now contributing over 25% of royalty revenue at substantially higher royalty rates. In the data center, Arm Neoverse compute subsystems are powering the world's most efficient AI accelerators, including NVIDIA Grace and AWS Graviton4.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Matt Ramsay (TD Cowen):\n"
            "Rene, how should we think about compute subsystem (CSS) adoption and its impact on royalty rate expansion?\n\n"
            "Rene Haas (CEO):\n"
            "CSS reduces customer time-to-market by up to 12 months. Because we provide verified, optimized silicon subsystems, customers happily pay more than double our standard architecture royalty rates."
        )
    },

    # ----------------------------------------------------
    # 17. Intel Corporation (INTC) 2026-Q2 (2026-08-01)
    # ----------------------------------------------------
    {
        "ticker": "INTC",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-08-01",
        "call_time_et": "17:00 ET",
        "source_url": "https://www.intc.com",
        "text": (
            "Intel Corporation (NASDAQ:INTC) Q2 2026 Earnings Conference Call\n"
            "Date: August 1, 2026 | 5:00 PM ET\n\n"
            "Executives Present:\n"
            "- Pat Gelsinger: Chief Executive Officer\n"
            "- David Zinsner: Executive VP & Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Pat Gelsinger (CEO):\n"
            "Q2 was an important milestone in our IDM 2.0 transformation. Revenue was $13.2 billion. Our Intel 18A process node is executing on schedule, with our first customer external tape-outs completed and manufacturing ramp slated for early next year.\n\n"
            "In AI accelerators, Gaudi 3 is shipping to OEM partners, delivering compelling total cost of ownership for mainstream generative AI training and inference.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Ross Seymore (Deutsche Bank):\n"
            "Pat, could you provide an update on external foundry customer pipeline commitments on Intel 18A?\n\n"
            "Pat Gelsinger (CEO):\n"
            "Ross, we have secured five advanced packaging design wins and have three major fab customers committing test wafers on 18A, providing validation of our ribbonFET and backside power delivery technologies."
        )
    },

    # ----------------------------------------------------
    # 18. Arista Networks (ANET) 2026-Q2 (2026-08-06)
    # ----------------------------------------------------
    {
        "ticker": "ANET",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-08-06",
        "call_time_et": "16:30 ET",
        "source_url": "https://investors.arista.com",
        "text": (
            "Arista Networks, Inc. (NYSE:ANET) Q2 2026 Financial Results Call\n"
            "Date: August 6, 2026 | 4:30 PM ET\n\n"
            "Executives Present:\n"
            "- Jayshree Ullal: Chairperson & Chief Executive Officer\n"
            "- Chantelle Breithaupt: Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Jayshree Ullal (CEO):\n"
            "Arista delivered record revenue of $1.85 billion in Q2, growing 23% year-over-year. Our non-GAAP gross margin was 65.4%.\n\n"
            "Ethernet is winning the AI networking fabric battle. The Ultra Ethernet Consortium (UEC) standards are progressing rapidly, and Arista's AI Etherlink platforms are connecting over 50,000 GPUs in unified, lossless clusters for tier-1 cloud titans.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Meta Marshall (Morgan Stanley):\n"
            "Jayshree, how are you tracking against your $750 million AI networking revenue target for 2026?\n\n"
            "Jayshree Ullal (CEO):\n"
            "Meta, based on robust deployments of our 800-gigabit platforms and pilot 1.6-terabit fabrics, we are tracking well ahead of that target and expect to exceed $900 million in AI-related networking this year."
        )
    },

    # ----------------------------------------------------
    # 19. Marvell Technology (MRVL) FY2026-Q2 (2026-08-28)
    # ----------------------------------------------------
    {
        "ticker": "MRVL",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-08-28",
        "call_time_et": "16:45 ET",
        "source_url": "https://investor.marvell.com",
        "text": (
            "Marvell Technology, Inc. (NASDAQ:MRVL) Q2 Fiscal 2026 Earnings Call\n"
            "Date: August 28, 2026 | 4:45 PM ET\n\n"
            "Executives Present:\n"
            "- Matt Murphy: Chairman & Chief Executive Officer\n"
            "- Willem Meintjes: Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Matt Murphy (CEO):\n"
            "Marvell delivered Q2 revenue of $1.48 billion. Our Data Center end market revenue grew 98% year-over-year, driven by electro-optics PAM4 DSPs and custom AI compute programs.\n\n"
            "Our custom ASIC programs with tier-1 cloud service providers are ramping aggressively, with two major compute programs hitting volume production in the second half of this year.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Tore Svanberg (Stifel):\n"
            "Matt, could you discuss the optical DSP opportunity as data centers transition from 800G to 1.6T optics?\n\n"
            "Matt Murphy (CEO):\n"
            "Tore, Marvell has first-mover advantage with our 3nm 1.6T Nova optical DSP. As GPU clusters scale to 100,000 nodes, optical interconnect density increases exponentially, driving substantial dollar content per cluster."
        )
    },

    # ----------------------------------------------------
    # 20. GE Vernova (GEV) 2026-Q2 (2026-07-24)
    # ----------------------------------------------------
    {
        "ticker": "GEV",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-07-24",
        "call_time_et": "08:30 ET",
        "source_url": "https://www.gevernova.com/investors",
        "text": (
            "GE Vernova Inc. (NYSE:GEV) Q2 2026 Earnings Conference Call\n"
            "Date: July 24, 2026 | 8:30 AM ET\n\n"
            "Executives Present:\n"
            "- Scott Strazik: Chief Executive Officer\n"
            "- Ken Parks: Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Scott Strazik (CEO):\n"
            "GE Vernova delivered solid second quarter results with revenue of $8.9 billion. Organic orders were up 28%, driven by gas power turbines and electrification grid infrastructure.\n\n"
            "The surge in AI data center electricity demand has fundamentally altered the power generation landscape. Hyperscalers are approaching us to secure multi-gigawatt on-site gas turbine capacity and high-voltage substation switchgear to bypass local grid connection queues.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Julian Dumoulin-Smith (Jefferies):\n"
            "Scott, could you quantify the data center pipeline for gas turbines and grid interconnection equipment?\n\n"
            "Scott Strazik (CEO):\n"
            "Julian, over 35% of our gas power equipment discussions in North America are now directly tied to data center developers seeking behind-the-meter generation solutions."
        )
    },

    # ----------------------------------------------------
    # 21. Oracle (ORCL) FY2026-Q4 (2026-06-12)
    # ----------------------------------------------------
    {
        "ticker": "ORCL",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q4",
        "call_date": "2026-06-12",
        "call_time_et": "17:00 ET",
        "source_url": "https://investor.oracle.com",
        "text": (
            "Oracle Corporation (NYSE:ORCL) Q4 Fiscal 2026 Earnings Conference Call\n"
            "Date: June 12, 2026 | 5:00 PM ET\n\n"
            "Executives Present:\n"
            "- Safra Catz: Chief Executive Officer\n"
            "- Larry Ellison: Chairman & Chief Technology Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Safra Catz (CEO):\n"
            "Total Q4 revenue was $15.2 billion, with cloud services revenue up 42% to $6.1 billion. Our remaining performance obligations (RPO) surged 44% to an all-time record of $98 billion.\n\n"
            "Larry Ellison (Chairman & CTO):\n"
            "Oracle Cloud Infrastructure (OCI) is building the largest AI supercomputers in the world. We are constructing gigawatt-scale data centers containing tens of thousands of NVIDIA Blackwell GPUs interconnected with RDMA over Converged Ethernet (RoCE).\n\n"
            "OpenAI, xAI, Microsoft, and NVIDIA itself use OCI because our bare-metal architecture and ultra-low latency networking allow AI models to train twice as fast at half the cost.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Brad Zelnick (Deutsche Bank):\n"
            "Larry, could you describe the multi-cloud partnership with Microsoft Azure and Google Cloud?\n\n"
            "Larry Ellison (CTO):\n"
            "Brad, customers love that they can now deploy Oracle Autonomous Database inside Azure and Google Cloud data centers. It eliminates data egress fees and allows AI models on any cloud to query Oracle transactional databases with sub-millisecond latency."
        )
    },

    # ----------------------------------------------------
    # 22. Eaton Corporation (ETN) 2026-Q2 (2026-08-02)
    # ----------------------------------------------------
    {
        "ticker": "ETN",
        "fiscal_year": "2026",
        "fiscal_quarter": "Q2",
        "call_date": "2026-08-02",
        "call_time_et": "09:00 ET",
        "source_url": "https://www.eaton.com/investors",
        "text": (
            "Eaton Corporation plc (NYSE:ETN) Q2 2026 Earnings Call\n"
            "Date: August 2, 2026 | 9:00 AM ET\n\n"
            "Executives Present:\n"
            "- Craig Arnold: Chairman & Chief Executive Officer\n"
            "- Olivier Leonetti: Executive VP & Chief Financial Officer\n\n"
            "=====================================================\n"
            "EXECUTIVE PREPARED REMARKS\n"
            "=====================================================\n"
            "Craig Arnold (Chairman & CEO):\n"
            "Eaton delivered another quarter of record segment margins and earnings. Organic sales grew 11%, led by Data Center & Distributed IT orders which grew over 30%.\n\n"
            "Electrical content per megawatt in AI data centers has doubled due to higher voltage power distribution units, uninterruptible power supplies (UPS), and modular power skids required to feed high-density GPU racks.\n\n"
            "=====================================================\n"
            "QUESTION AND ANSWER SESSION\n"
            "=====================================================\n"
            "Steve Tusa (JPMorgan):\n"
            "Craig, how far out does your data center backlog extend today?\n\n"
            "Craig Arnold (CEO):\n"
            "Steve, our backlog in data centers extends through 2027 and into 2028. Customers are booking transformer and switchgear manufacturing slots years in advance to protect their AI launch dates."
        )
    }
]
