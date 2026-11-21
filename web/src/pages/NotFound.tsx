import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-[1400px] flex-col justify-center px-5 py-28 md:px-10">
      <span className="label-accent">404</span>
      <h1 className="display mt-5 max-w-[16ch] text-balance text-[2.5rem] leading-tight md:text-[4rem]">
        Nothing in the lab is at this address.
      </h1>
      <p className="mt-5 max-w-[52ch] text-[0.9375rem] leading-relaxed text-ink-400">
        Press ⌘K to search indicators, banks, research sections and glossary terms, or start from the entrance.
      </p>
      <div className="mt-8 flex flex-wrap gap-2">
        <Link to="/" className="btn btn-primary">
          Home
        </Link>
        <Link to="/models" className="btn">
          The Model Lab
        </Link>
        <Link to="/data" className="btn">
          Data Explorer
        </Link>
      </div>
    </div>
  );
}
