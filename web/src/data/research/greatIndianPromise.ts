import type { Paper } from './types';

export const GREAT_INDIAN_PROMISE: Paper = {
  slug: 'the-great-indian-promise',
  title: 'The Great Indian Promise',
  subtitle:
    'Income can rise without wealth accumulating at the same pace. The missing link is ownership.',
  author: 'India Economics Intelligence Lab',
  affiliation: 'Independent economics research',
  date: '2026-09-24',
  readingMinutes: 18,
  category: 'Wealth',
  tags: ['wealth', 'inequality', 'household finance', 'ownership', 'savings'],
  abstract:
    'India’s per-capita income has risen for three decades, and household saving rates are high by international standards. Household wealth has not compounded at a comparable pace. This paper argues that the gap is not primarily a saving gap but a composition gap: the average Indian household holds roughly 88% of its assets in property and gold and about 5% in financial assets. Physical assets store value; they do not compound in the way a financial claim does, and they cannot be added to in small, regular increments. Using the household portfolio measured by the RBI’s Household Finance Committee and a transparent accumulation model, we show that a household saving ₹1,00,000 a year for thirty years ends with materially different wealth depending only on where those savings sit — with no change in income, saving rate or discipline. The result is a statement about the arithmetic of portfolio composition, conditional on the return assumptions entered, not a forecast and not advice. We set out the assumptions explicitly and make the model editable so that a reader can test the claim against their own.',
  question:
    'If Indian households save as much as households elsewhere, why does household wealth accumulate more slowly — and how much of the difference is explained by what they save into rather than how much they save?',
  sections: [
    {
      id: 'introduction',
      navLabel: 'Introduction',
      title: 'Introduction',
      blocks: [
        {
          kind: 'lead',
          text: 'The promise is simple and it is mostly true: work, save, and you will build wealth. India has delivered the first two conditions at scale. The third has been slower to arrive, and the reason is not the one most often given.',
        },
        {
          kind: 'p',
          text: 'India’s gross domestic savings rate was 34.2% of gross national disposable income in FY2024-25 [1]. That is high — higher than most advanced economies and comfortably above the world average. Household net financial savings recovered to 7.0% of GNDI in the same year, from 5.8% a year earlier [1]. Real GDP grew 7.7% in FY2025-26 on the latest official vintage [2]. On the conventional account, a country that grows at this rate and saves at this rate should be accumulating household wealth quickly.',
        },
        {
          kind: 'p',
          text: 'The conventional account is incomplete because it treats saving as a single quantity. It is not. A rupee saved into a fixed deposit, a rupee saved into a provident fund and a rupee saved into a second plot of land are all counted as saving, and they behave completely differently over thirty years. The first two are claims that compound automatically. The third is an asset whose value moves with a local property market, which cannot be bought in small increments, cannot be sold in part, and yields nothing at all unless it is let.',
        },
        {
          kind: 'p',
          text: 'The RBI’s Household Finance Committee measured how Indian households actually allocate. The average household holds about 77% of its assets in real estate, 11% in gold, and roughly 5% in financial assets, with the remainder in other physical assets [3]. The All India Debt and Investment Survey reaches nearly the same place by an entirely different route: financial assets are about 4.6% of rural household assets and 9.3% of urban [4]. Two independent instruments, a decade apart, agree that the Indian household balance sheet is overwhelmingly physical.',
        },
        {
          kind: 'p',
          text: 'This paper takes that composition seriously as an economic fact and asks what it implies mechanically. The exercise is deliberately modest in its ambition: we are not estimating a causal effect, and we are not forecasting returns. We are asking what thirty years of identical saving produces under different allocations, using assumptions we state in full and let the reader overwrite.',
        },
        {
          kind: 'callout',
          title: 'What this paper does not claim',
          tone: 'caution',
          text: 'It does not claim that financial assets will outperform property over the next thirty years. It does not claim households are behaving irrationally — a house is consumed as shelter and gold is collateral that a bank will lend against at short notice, and neither service shows up in a return series. It claims only that composition has a large arithmetic consequence that is usually left implicit, and that the consequence is worth making explicit and testable.',
        },
      ],
    },
    {
      id: 'question',
      navLabel: 'Research Question',
      title: 'Research Question',
      blocks: [
        {
          kind: 'quote',
          text: 'If Indian households save as much as households elsewhere, why does household wealth accumulate more slowly — and how much of the difference is explained by what they save into rather than how much they save?',
        },
        {
          kind: 'p',
          text: 'The question has three parts, and this paper answers only the third cleanly. The first — whether Indian household wealth does in fact accumulate more slowly — is a measurement question that Indian survey data answers poorly, for reasons set out under Limitations. The second — why households allocate as they do — is a behavioural and institutional question with a substantial literature behind it. The third is arithmetic, and arithmetic is where a model earns its place: given an allocation and a set of returns, the terminal wealth is determined, and the sensitivity of that terminal wealth to the allocation can be computed exactly.',
        },
        {
          kind: 'p',
          text: 'So the operational question is: holding income, saving rate and horizon fixed, how much does terminal household wealth vary with portfolio composition alone?',
        },
      ],
    },
    {
      id: 'context',
      navLabel: 'Literature & Context',
      title: 'Literature and Context',
      blocks: [
        {
          kind: 'p',
          text: 'The Household Finance Committee’s 2017 report remains the most complete official account of the Indian household balance sheet [3]. Its central finding — that Indian households hold an unusually large share of wealth in non-financial assets, and that this is costly — frames the argument here. The Committee drew the comparison explicitly: households in advanced economies hold a far larger share in financial claims and pension entitlements, and the difference is not explained by income levels alone.',
        },
        {
          kind: 'p',
          text: 'The All India Debt and Investment Survey provides the independent measurement [4]. AIDIS 2019 surveyed 69,455 rural and 47,006 urban households and recorded assets as of 30 June 2018. It found average physical assets of ₹15,19,771 against financial assets of ₹72,608 per rural household, and ₹24,65,277 against ₹2,51,804 per urban household. The survey also found that as household wealth rises, the additional accumulation goes further into physical assets, with real estate preferred over gold — and that even for the wealthiest households, financial holdings remain modest.',
        },
        {
          kind: 'p',
          text: 'Against that, the flow data show a genuine shift underway. Monthly SIP contributions reached ₹32,297 crore in August 2026 with contributing accounts above 10 crore [5], and industry assets under management stood at ₹87.08 lakh crore [5]. Demat accounts across the two depositories numbered roughly 23 crore by mid-2026 [6]. These are large numbers, and they are why this question is worth asking now rather than in 2017.',
        },
        {
          kind: 'p',
          text: 'They should not be over-read. Account counts include duplicates and dormant accounts; AUM growth blends flows with market returns; and a flow of ₹3.9 lakh crore a year is meaningful against household saving but small against a stock of household wealth dominated by land and buildings. The composition described by the Committee is a stock, and stocks move slowly even under sustained flows. That is precisely why the arithmetic of composition compounds over a working lifetime rather than a business cycle.',
        },
        {
          kind: 'p',
          text: 'One further piece of context matters for interpreting the savings data. Net household financial savings improved in FY2024-25, but gross financial savings fell, from 12.1% to 11.8% of GNDI [1]. The entire improvement came from the liability side, where household borrowing dropped from 6.4% to 4.8%. Households did not save more that year; they borrowed less. A headline that reads as rising thrift is, on inspection, deleveraging.',
        },
      ],
    },
    {
      id: 'methodology',
      navLabel: 'Methodology',
      title: 'Methodology',
      blocks: [
        {
          kind: 'p',
          text: 'The model is a deterministic accumulation of a level annual contribution across a fixed portfolio, rebalanced annually to target weights. It is chosen for transparency rather than realism: every step can be checked by hand, and every output can be traced back to an input the reader controls.',
        },
        { kind: 'h3', text: 'Portfolio return' },
        {
          kind: 'p',
          text: 'The portfolio earns the weighted average of its components’ nominal returns:',
        },
        {
          kind: 'equation',
          latex: 'R_p=\\sum_i w_i R_i',
          ascii: 'R_p = Σ wᵢ Rᵢ',
          caption: 'wᵢ is the target weight of asset i; Rᵢ its assumed nominal annual return. Weights must sum to 1.',
        },
        {
          kind: 'p',
          text: 'Annual rebalancing to target is what makes this the governing return. Without it, the highest-returning asset drifts upward in weight and the portfolio return is path-dependent; with it, R_p is constant and the decomposition stays interpretable. Rebalancing is an assumption, and a strong one for a household that owns a house it cannot sell a tenth of. We return to this under Limitations.',
        },
        { kind: 'h3', text: 'Accumulation' },
        {
          kind: 'p',
          text: 'For a contribution C made at the end of each of n years, terminal wealth is the standard annuity future value:',
        },
        {
          kind: 'equation',
          latex: 'FV=C\\,\\frac{(1+r)^{n}-1}{r}',
          ascii: 'FV = C · [ (1+r)ⁿ − 1 ] / r',
          caption: 'With r = R_p. At r = 0 the expression takes its limiting value C·n.',
        },
        {
          kind: 'p',
          text: 'The implementation accumulates period by period rather than evaluating the closed form, because that generalises to an opening balance, to start-of-period contributions and to contribution frequencies finer than annual. It agrees with the closed form to within floating-point tolerance in the case the closed form covers, and a test asserts exactly that.',
        },
        { kind: 'h3', text: 'Identification and what the model can support' },
        {
          kind: 'p',
          text: 'This is an accounting model, not an econometric one. It identifies no causal parameter and estimates nothing. Its outputs are implications of its inputs. The appropriate reading of a comparison between two allocations is: <em>under these assumed returns, this is the difference composition makes</em> — and the honest test of whether the difference is robust is to change the assumed returns and see whether it survives.',
        },
        {
          kind: 'p',
          text: 'The figure below makes that test one drag of a slider rather than a re-run of a spreadsheet, which is the whole point of publishing a model instead of a table.',
        },
        {
          kind: 'link',
          to: '/models/bfpi/methodology',
          label: 'The companion methodology →',
          sublabel: 'The BFPI banking index uses the same show-your-work discipline on a composite index.',
        },
      ],
    },
    {
      id: 'data',
      navLabel: 'Data',
      title: 'Data',
      blocks: [
        {
          kind: 'p',
          text: 'Two classes of input enter the model, and the distinction between them is the most important thing on this page.',
        },
        {
          kind: 'table',
          head: ['Variable', 'Value', 'Class', 'Source'],
          rows: [
            ['Property share', '77%', 'OBSERVED', 'RBI Household Finance Committee [3]'],
            ['Gold share', '11%', 'OBSERVED', 'RBI Household Finance Committee [3]'],
            ['Financial-asset share', '5%', 'OBSERVED', 'RBI Household Finance Committee [3]'],
            ['Other physical share', '7%', 'DERIVED', 'Residual of the above [3]'],
            ['Property return', '5.5% p.a.', 'ASSUMPTION', 'Anchored to RBI House Price Index [7]'],
            ['Gold return', '10.0% p.a.', 'ASSUMPTION', 'Anchored to long-run rupee gold prices'],
            ['Financial return', '9.5% p.a.', 'ASSUMPTION', 'Anchored to Nifty 50 TRI and deposit rates [8]'],
            ['Other physical return', '0.0% p.a.', 'ASSUMPTION', 'Modelling convention'],
            ['Annual saving', '₹1,00,000', 'ASSUMPTION', 'Stated premise of the figure'],
            ['Horizon', '30 years', 'ASSUMPTION', 'Approximately one working lifetime'],
          ],
          caption:
            'Allocation is observed. Returns are not. Every assumed return is set at or below its historical anchor, because a thirty-year projection that assumes the best decades on record repeat is a forecast wearing the clothes of arithmetic.',
        },
        {
          kind: 'p',
          text: 'The anchors deserve scrutiny. The RBI’s All-India House Price Index grew about 3.7% a year through 2017–2020 and 2.2% year on year in Q2:2025-26, after double-digit growth in the early 2010s [7]; the 5.5% default sits between those regimes and above the recent run-rate. Rupee gold compounded at roughly 11–13% a year over the twenty years to 2026, a window containing two exceptional bull runs; the 10.0% default is below it. The Nifty 50 total-return index returned about 12.4% a year over the twenty years to February 2026 [8], but a household financial portfolio is mostly deposits, provident fund and insurance rather than index equity, so the 9.5% default reflects that blend and not the equity line.',
        },
        {
          kind: 'callout',
          title: 'Why the property assumption is the one to argue with',
          text: 'The result in this paper is sensitive to the property return above all, because property is 77% of the portfolio. Raise it to 9% and the composition effect shrinks sharply; the model will show you that in real time. The honest position is that nobody knows the thirty-year return on Indian residential property, and a reader who believes it will beat financial assets should set it accordingly and read the figure again.',
        },
      ],
    },
    {
      id: 'figure2',
      navLabel: 'Figure 2',
      title: 'Figure 2 — Household Wealth Accumulation',
      blocks: [
        {
          kind: 'p',
          text: 'The central exhibit. It asks a single question: what happens when ₹1 lakh is saved every year for thirty years? The answer depends entirely on where the money goes, and the figure lets you move it.',
        },
        {
          kind: 'figure',
          figure: 'figure2',
          title: 'Figure 2',
          caption:
            'Household wealth accumulation under the observed Indian portfolio, and under any portfolio you specify. Total contributed is fixed at ₹30,00,000 throughout; everything that separates the curves is composition.',
        },
        {
          kind: 'p',
          text: 'At the observed allocation the portfolio earns a weighted nominal return of 5.81% — 77% of the portfolio in an asset assumed to return 5.5%, and 5% in the asset assumed to return 9.5%, pulls the average down close to the property return. The gold holding does most of the work of lifting it.',
        },
        {
          kind: 'p',
          text: 'Move fifteen percentage points from property into financial assets — from the observed 5% to 20%, leaving gold and other physical assets untouched — and the weighted return rises to 6.41%. That is a difference of 60 basis points a year. Over thirty years of contributions it is worth roughly ₹8.5 lakh on ₹30 lakh contributed: about a 28% larger terminal balance, from no additional saving whatsoever.',
        },
        {
          kind: 'p',
          text: 'Sixty basis points is a small number that becomes a large one only because it is applied for thirty years to a growing balance. That is the entire mechanism, and it is why the composition of the balance sheet is a more consequential household decision than the marginal saving rate for most families who already save.',
        },
      ],
    },
    {
      id: 'analysis',
      navLabel: 'Analysis',
      title: 'Analysis',
      blocks: [
        {
          kind: 'h3', text: 'The gap is a composition gap, not a discipline gap' },
        {
          kind: 'p',
          text: 'The comparison above holds income, saving rate, horizon and contribution timing constant. Nothing about household behaviour changes except where the saved rupee lands. Under the stated assumptions, that single choice accounts for a difference of roughly a quarter to a third in terminal wealth. It is difficult to find a change in saving rate that a median household could plausibly achieve which would produce as large an effect.',
        },
        { kind: 'h3', text: 'Why physical assets do not compound the same way' },
        {
          kind: 'p',
          text: 'Three properties separate the buckets, and only the first shows up in a return series.',
        },
        {
          kind: 'list',
          items: [
            'Divisibility. ₹8,000 a month can be added to a provident fund or a SIP. It cannot be added to a plot of land. A household saving in property saves in lumps, with the balance sitting idle between purchases — an implicit cost the return series never records.',
            'Automatic reinvestment. A financial claim reinvests its own yield by construction. Property yields rent only if let, and gold yields nothing at all; the return on both is realised only on sale, which for a primary dwelling is rarely.',
            'Liquidity at the wrong moment. Households sell what they can when they need cash. Gold’s role as instant collateral is real economic value, and it is a reason the 11% allocation is rational even though it is not the return-maximising choice.',
          ],
        },
        { kind: 'h3', text: 'The flows are moving; the stock is not, yet' },
        {
          kind: 'p',
          text: 'SIP contributions above ₹32,000 crore a month [5] are roughly ₹3.9 lakh crore a year entering financial assets through an automatic, divisible channel — precisely the mechanism the composition argument says is missing. That is a genuine structural change in how Indian households save, and it did not exist at this scale when the Household Finance Committee reported.',
        },
        {
          kind: 'p',
          text: 'But a stock dominated by land and buildings does not re-weight quickly. Even sustained flows of this size move the aggregate share by a small number of percentage points a year against a property stock accumulated over generations. The households capturing the composition effect today are disproportionately the ones who were already going to accumulate; whether the shift reaches the median household is an open empirical question, and the demat and SIP account counts do not answer it, because they count accounts rather than people.',
        },
        { kind: 'h3', text: 'What the ownership framing adds' },
        {
          kind: 'p',
          text: 'Calling this a problem of ownership rather than of saving changes what follows from it. If the binding constraint were saving, the policy response would be to raise saving incentives. If it is composition, the relevant questions are about access, divisibility, trust and default options — whether a household can put ₹500 into a claim that compounds without visiting a branch, and whether the default path of least resistance for a marginal rupee leads to a deposit or to gold.',
        },
      ],
    },
    {
      id: 'discussion',
      navLabel: 'Discussion',
      title: 'Discussion',
      blocks: [
        {
          kind: 'p',
          text: 'The most serious objection to this paper is that it compares returns while ignoring what the assets are for. A house is not a low-yielding asset; it is shelter, purchased as a consumption good that happens to store value. Gold is not an underperforming commodity; it is collateral a household can borrow against within a day, in a country where a large share of households cannot borrow unsecured at reasonable rates. Neither service appears in a return series, and a model that prices only returns will systematically undervalue both.',
        },
        {
          kind: 'p',
          text: 'We accept the objection and think it narrows the claim without defeating it. The model does not say households should hold no property or no gold. It says that the marginal allocation decision — where the next rupee of savings goes, once shelter is secured and a precautionary gold buffer exists — carries a larger long-run consequence than it is usually given credit for. A household that owns its home and moves its subsequent savings from a third plot of land into a compounding claim is not giving up shelter or liquidity.',
        },
        {
          kind: 'p',
          text: 'A second objection is that the returns are assumed, so the result is assumed. This is true and is the reason the figure is interactive. The defence is not that our assumptions are correct but that they are visible, conservative relative to their historical anchors, and overridable in one gesture. A reader who sets property to 9% and financial assets to 7% will find the composition effect largely disappears — and will have learned something precise about which assumption the argument rests on.',
        },
        {
          kind: 'p',
          text: 'A third objection concerns distribution. Everything here describes a representative household. Composition varies enormously across the wealth distribution: the top of the distribution already holds financial assets and equity, and the bottom holds neither property nor financial assets in meaningful quantity. The composition effect, if real, therefore widens rather than narrows wealth inequality — those best placed to capture it are those who already hold the compounding assets. That is a consequence of the argument, not an objection to it, and it deserves separate treatment.',
        },
      ],
    },
    {
      id: 'limitations',
      navLabel: 'Limitations',
      title: 'Limitations',
      blocks: [
        {
          kind: 'list',
          items: [
            'The allocation is measured; the returns are assumed. No result here is an observation about the future, and a thirty-year projection is an illustration of arithmetic rather than a forecast.',
            'The model is deterministic. Real returns are volatile and correlated, and sequence-of-returns risk means two portfolios with identical average returns can end at very different places. A stochastic treatment would widen every number here into a distribution.',
            'Annual rebalancing to target is assumed. A household cannot sell a tenth of a house. Without rebalancing the portfolio drifts toward its highest-returning asset, and the effect shown here is a lower bound in some paths and an upper bound in others.',
            'Taxes, transaction costs, stamp duty, brokerage, fund expense ratios and capital-gains treatment are all omitted. These do not fall equally across the buckets — property transactions carry stamp duty that financial purchases do not, and that cuts against property further.',
            'The RBI Household Finance Committee figures date from 2017. The AIDIS survey recorded assets as of 30 June 2018. Both predate the SIP expansion described in the Analysis, so the observed allocation is a starting point rather than a current reading.',
            'Top-tail wealth is systematically undercovered in Indian household surveys. Averages drawn from them understate concentration, and the "average household" in this paper is a construct that may not correspond to any real family.',
            'Property returns are measured by index and are poorly identified at household level. Housing markets are local, illiquid and heterogeneous; a national index conceals enormous dispersion, and the return an individual household actually realised is largely unobservable.',
            'No causal claim is made or supported anywhere in this paper. Nothing here identifies why households allocate as they do, and the model cannot distinguish a preference from a constraint.',
          ],
        },
      ],
    },
    {
      id: 'conclusion',
      navLabel: 'Conclusion',
      title: 'Conclusion',
      blocks: [
        {
          kind: 'p',
          text: 'India saves. The evidence on that is not in dispute: a domestic savings rate above 34% of national disposable income [1] places India among the high-saving economies. The promise that saving builds wealth is not failing because households lack discipline.',
        },
        {
          kind: 'p',
          text: 'It is constrained by where the saving goes. A portfolio that is 88% physical stores value competently and compounds poorly. Under the assumptions set out here — each stated, each anchored below its historical range, each editable — moving fifteen percentage points of a household portfolio from property into financial assets raises terminal wealth after thirty years by roughly 28%, on identical contributions. The effect comes from 60 basis points of annual return applied for a working lifetime.',
        },
        {
          kind: 'p',
          text: 'That is an arithmetic claim, and arithmetic claims are the kind a reader should be able to check rather than accept. Every number in this paper is computed live from inputs shown on the page. Change the property return and the argument weakens; change the horizon and it shortens; set the returns equal and it vanishes entirely, as it should. We would rather publish a model a reader can break than a table they must trust.',
        },
        {
          kind: 'callout',
          title: 'Conditional on your assumptions',
          tone: 'caution',
          text: 'Every result shown in the interactive figure depends on the inputs entered. Historical returns do not guarantee future performance. Nothing in this paper is financial advice, and no allocation shown here is a recommendation.',
        },
      ],
    },
  ],
  citations: [
    {
      n: 1,
      text: 'Annual Report 2024-25 — household financial savings, gross domestic savings and household financial liabilities as a share of gross national disposable income.',
      publisher: 'Reserve Bank of India',
      year: '2025',
      url: 'https://www.rbi.org.in/Scripts/AnnualReportMainDisplay.aspx',
    },
    {
      n: 2,
      text: 'National Accounts Statistics — Provisional Estimates of annual GDP for 2025-26 (real growth 7.7%), superseding the First Advance Estimate of 7.4%.',
      publisher: 'MoSPI / National Statistical Office',
      year: '2026',
      url: 'https://www.mospi.gov.in/',
    },
    {
      n: 3,
      text: 'Report of the Household Finance Committee — Indian Household Finance. Finds the average Indian household holds approximately 77% of assets in real estate, 11% in gold and about 5% in financial assets.',
      publisher: 'Reserve Bank of India',
      year: '2017',
      url: 'https://rbidocs.rbi.org.in/rdocs/PublicationReport/Pdfs/HFCRA28D0415E2144A009112DD314ECF5C07.PDF',
    },
    {
      n: 4,
      text: 'All India Debt & Investment Survey, NSS 77th round (January–December 2019), NSS Report No. 588. Average physical and financial assets per household, rural and urban.',
      publisher: 'MoSPI / National Statistical Office',
      year: '2021',
      url: 'https://www.mospi.gov.in/sites/default/files/press_release/press_note-AIDIS-240821.pdf',
    },
    {
      n: 5,
      text: 'Monthly industry data — net assets under management of ₹87.08 lakh crore and SIP contributions of ₹32,297 crore for August 2026.',
      publisher: 'Association of Mutual Funds in India (AMFI)',
      year: '2026',
      url: 'https://www.amfiindia.com/indian-mutual',
    },
    {
      n: 6,
      text: 'Depository periodic statistics — demat accounts serviced by CDSL and NSDL.',
      publisher: 'CDSL / NSDL',
      year: '2026',
      url: 'https://www.cdslindia.com/publications/periodicstats.aspx',
    },
    {
      n: 7,
      text: 'All-India House Price Index — quarterly releases. Annual growth of 2.2% in Q2:2025-26 against 7% a year earlier.',
      publisher: 'Reserve Bank of India',
      year: '2026',
      url: 'https://www.rbi.org.in/Scripts/PublicationsView.aspx',
    },
    {
      n: 8,
      text: 'Nifty 50 Total Return Index — long-run annualised returns.',
      publisher: 'NSE Indices',
      year: '2026',
      url: 'https://www.nseindia.com/products-services/indices-nifty50-index',
    },
  ],
};
