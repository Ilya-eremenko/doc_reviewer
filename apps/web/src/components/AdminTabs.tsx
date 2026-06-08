"use client";

import Link from "next/link";

const adminLinks = [
  ["/admin/users", "Users"],
  ["/admin/documents", "Documents"],
  ["/admin/analyses", "Analyses"],
  ["/admin/skills", "Skills"],
  ["/admin/etalons", "Etalons"],
  ["/admin/benchmarks", "Benchmarks"],
  ["/admin/feedback", "Feedback"],
];

export function AdminTabs() {
  return (
    <nav className="admin-tabs" aria-label="Admin sections">
      {adminLinks.map(([href, label]) => (
        <Link className="secondary-link" href={href} key={href}>
          {label}
        </Link>
      ))}
    </nav>
  );
}
