import { useEffect, useRef, useState } from "react";
import { ParkingSquare } from "lucide-react";
import ResultsSection from "./components/ResultsSection.jsx";
import SearchPanel from "./components/SearchPanel.jsx";
import {
  getConfiguredParkingMode,
  getParkingResults,
} from "./services/parkingResultsProvider.js";

function SiteHeader() {
  return (
    <header className="site-header">
      <a className="brand" href="#main" aria-label="ParkSmart AI home">
        <span className="brand-mark" aria-hidden="true">
          <ParkingSquare size={21} strokeWidth={1.8} />
        </span>
        <span className="brand-name">
          ParkSmart <span>AI</span>
        </span>
      </a>
      <a className="header-action" href="#parking-search">
        Plan a search <span aria-hidden="true">↘</span>
      </a>
    </header>
  );
}

function ParkingIllustration() {
  return (
    <div className="illustration" aria-label="Illustration of a city parking garage" role="img">
      <div className="illustration-label">
        <span className="label-dot" />
        BUILT AROUND YOUR ARRIVAL
      </div>
      <svg
        className="garage-art"
        viewBox="0 0 520 490"
        fill="none"
        role="presentation"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M0 389.5H520" stroke="currentColor" strokeOpacity=".18" />
        <path d="M55 389.5V179.2L192 104V389.5" fill="#DCE7D9" />
        <path d="M55 179.2L192 104V389.5" stroke="#52725C" strokeWidth="2" />
        <path d="M77 191.5L170 140.5V190L77 241V191.5Z" fill="#F5F5F0" />
        <path d="M77 255.5L170 204.5V254L77 305V255.5Z" fill="#F5F5F0" />
        <path d="M77 319.5L170 268.5V318L77 369V319.5Z" fill="#F5F5F0" />
        <path d="M191 389.5V163.2L343 96V389.5" fill="#E7E9DD" />
        <path d="M191 163.2L343 96V389.5" stroke="#52725C" strokeWidth="2" />
        <path d="M214 185L320 138V190L214 237V185Z" fill="#F5F5F0" />
        <path d="M214 254L320 207V259L214 306V254Z" fill="#F5F5F0" />
        <path d="M214 323L320 276V328L214 375V323Z" fill="#F5F5F0" />
        <path d="M343 389.5V221L458 168V389.5" fill="#DCE7D9" />
        <path d="M343 221L458 168V389.5" stroke="#52725C" strokeWidth="2" />
        <path d="M366 244L435 212V262L366 294V244Z" fill="#F5F5F0" />
        <path d="M366 311L435 279V329L366 361V311Z" fill="#F5F5F0" />
        <path d="M55 389.5H458" stroke="#315744" strokeWidth="2" />
        <path d="M35 389.5H485" stroke="#315744" strokeWidth="3" />
        <rect x="372" y="40" width="90" height="90" rx="2" fill="#315744" />
        <path d="M416.5 58.5C403.8 58.5 395.5 66.9 395.5 79.5V110.5H407V96.8H426.1C437.8 96.8 444.5 90.6 444.5 79.7C444.5 66.8 435.2 58.5 421.5 58.5H416.5ZM416.4 68.8H421.6C429 68.8 433 72.5 433 79.6C433 84.4 430.8 86.5 425.8 86.5H407V79.5C407 72.7 410.3 68.8 416.4 68.8Z" fill="#F5F5F0" />
        <path d="M126 415H381" stroke="#315744" strokeOpacity=".24" strokeDasharray="3 8" />
      </svg>
      <div className="illustration-caption">
        <span className="caption-rule" />
        A better arrival starts with a better plan.
      </div>
    </div>
  );
}

function App() {
  const [search, setSearch] = useState(null);
  const requestId = useRef(0);
  const requestController = useRef(null);

  useEffect(
    () => () => {
      requestController.current?.abort();
    },
    [],
  );

  function handleSearch(criteria) {
    requestId.current += 1;
    const currentRequestId = requestId.current;
    requestController.current?.abort();

    if (!criteria) {
      requestController.current = null;
      setSearch(null);
      return;
    }

    const controller = new AbortController();
    requestController.current = controller;
    const mode = getConfiguredParkingMode();
    setSearch({ criteria, mode, status: "loading", results: [] });

    getParkingResults(criteria, { signal: controller.signal })
      .then(({ mode: resultMode, results }) => {
        if (requestId.current !== currentRequestId || controller.signal.aborted) {
          return;
        }
        setSearch({ criteria, mode: resultMode, status: "success", results });
      })
      .catch((error) => {
        if (requestId.current !== currentRequestId || controller.signal.aborted) {
          return;
        }
        setSearch({
          criteria,
          mode,
          status: "error",
          results: [],
          error: error instanceof Error ? error.message : "Unable to load parking results.",
        });
      });
  }

  return (
    <div className="app-shell">
      <SiteHeader />
      <main id="main">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow">
              <span className="eyebrow-line" />
              PARKING, PLANNED AROUND YOU
            </p>
            <h1 id="hero-title">
              Make room for
              <br />
              a <em>better arrival.</em>
            </h1>
            <p className="hero-description">
              Tell us where you’re headed and when. ParkSmart AI is being built to help you find a
              parking option that fits your plans.
            </p>
            <SearchPanel onSearch={handleSearch} />
          </div>
          <ParkingIllustration />
        </section>
        {search && (
          <ResultsSection
            criteria={search.criteria}
            mode={search.mode}
            status={search.status}
            results={search.results}
            error={search.error}
            onRetry={() => handleSearch(search.criteria)}
          />
        )}
      </main>
      <footer className="site-footer">
        <span>ParkSmart AI</span>
        <span className="footer-note">A thoughtful start to getting there.</span>
      </footer>
    </div>
  );
}

export default App;
