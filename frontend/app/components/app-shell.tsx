"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bookmark, Compass, PlaneTakeoff, Settings2, Route } from "lucide-react";

const links = [
  { href: "/", label: "Search journeys", icon: PlaneTakeoff },
  { href: "/saved", label: "Saved journeys", icon: Bookmark },
  { href: "/layovers", label: "Layover explorer", icon: Compass },
  { href: "/settings", label: "Settings & status", icon: Settings2 },
];

const pageNames: Record<string, string> = {
  "/": "Search journeys",
  "/results": "Journey results",
  "/saved": "Saved journeys",
  "/layovers": "Layover explorer",
  "/settings": "Settings & status",
};

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const pageName = pageNames[pathname] ?? "Search journeys";

  return (
    <div className="app-frame">
      <aside className="sidebar" aria-label="Main navigation">
        <Link href="/" className="brand" aria-label="FDR home">
          <span className="brand-mark"><Route size={18} strokeWidth={2} /></span>
          <span><span className="brand-name">FDR</span><span className="brand-subtitle">Journey planning</span></span>
        </Link>
        <div className="nav-label">Workspace</div>
        <nav className="side-nav" aria-label="Workspace">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link key={href} href={href} className={active ? "nav-link nav-link-active" : "nav-link"} aria-current={active ? "page" : undefined}>
                <Icon className="nav-icon" aria-hidden="true" />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="provider-note">
            <span className="provider-dot" aria-hidden="true" />
            <div><strong>Live data not connected</strong><span>Search results will appear once a travel provider is configured.</span></div>
          </div>
          <div className="sidebar-foot">FDR · Travel intelligence</div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>FDR</span><span aria-hidden="true">/</span><strong>{pageName}</strong></div>
          <div className="topbar-meta"><span className="topbar-indicator" aria-hidden="true" />Search providers are currently offline</div>
        </header>
        {children}
      </div>
    </div>
  );
}

export function PageIntro({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div>
      <div className="page-eyebrow"><span className="eyebrow-rule" />{eyebrow}</div>
      <h1 className="page-title">{title}</h1>
      <p className="page-subtitle">{description}</p>
    </div>
  );
}

export function EmptyPage({ eyebrow, title, description, detail }: { eyebrow: string; title: string; description: string; detail: string }) {
  return (
    <AppShell>
      <main className="page-content secondary-page">
        <PageIntro eyebrow={eyebrow} title={title} description={description} />
        <section className="surface secondary-panel">
          <h2>Not available yet</h2>
          <p>{detail}</p>
          <div className="integration-line"><span className="provider-dot" aria-hidden="true" />This feature is not connected to live travel data.</div>
        </section>
      </main>
    </AppShell>
  );
}
