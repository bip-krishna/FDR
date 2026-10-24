import { EmptyPage } from "../components/app-shell";

export default function SettingsPage() {
  return <EmptyPage eyebrow="Provider readiness" title="Settings & status." description="Understand which travel sources are connected before relying on a search." detail="No provider credentials have been configured. Provider controls and usage accounting are scheduled for later stages; no external requests are currently made." />;
}
