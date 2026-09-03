"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const pathname = usePathname();

  // Don't render navbar on login/register pages
  if (pathname === "/login" || pathname === "/register" || !isAuthenticated) {
    return null;
  }

  const navItems = [
    { label: "Workflows", href: "/workflows" },
    { label: "Jobs", href: "/jobs" },
  ];

  if (user?.role === "admin") {
    navItems.push({ label: "Dead Letters", href: "/dead-letters" });
  }

  return (
    <header className="border-b border-gray-800 bg-gray-950 text-gray-100">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center space-x-8">
          <Link href="/workflows" className="flex items-center space-x-2 text-xl font-bold tracking-tight text-white hover:text-indigo-400">
            <span className="bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
              FlowForge
            </span>
          </Link>

          <nav className="flex space-x-4">
            {navItems.map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    active
                      ? "bg-gray-800 text-white"
                      : "text-gray-400 hover:bg-gray-900 hover:text-gray-200"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-sm text-gray-400">
            <span>{user?.email}</span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${
                user?.role === "admin"
                  ? "bg-purple-900/60 text-purple-300 border border-purple-700"
                  : "bg-gray-800 text-gray-300"
              }`}
            >
              {user?.role}
            </span>
          </div>

          <button
            onClick={logout}
            className="rounded bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-300 hover:bg-red-950 hover:text-red-300 transition"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
