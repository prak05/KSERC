import { TopBar } from "@/components/layout/TopBar";
import { Sidebar } from "@/components/layout/Sidebar";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex min-h-screen bg-page text-tx font-sans">
            <TopBar />
            <div className="flex w-full mt-[60px]">
                <Sidebar />
                <main className="ml-[216px] flex-1 p-6 pb-16 min-w-0">
                    {children}
                </main>
            </div>
        </div>
    );
}
