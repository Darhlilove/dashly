import { useState, memo } from "react";
import Sidebar from "./Sidebar";
import ConversationPane from "./ConversationPane";
import { Dashboard } from "../types";

interface Message {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface MainLayoutProps {
  // Sidebar props
  savedDashboards: Dashboard[];
  onLoadDashboard: (dashboard: Dashboard) => void;
  onNewDashboard: () => void;
  currentDashboardId?: string;

  // Conversation props
  messages: Message[];
  onSendMessage: (message: string) => void;
  isLoading: boolean;

  // Main content
  children: React.ReactNode;

  // Layout state
  showConversation: boolean;
}

const MainLayout = memo(function MainLayout({
  savedDashboards,
  onLoadDashboard,
  onNewDashboard,
  currentDashboardId,
  messages,
  onSendMessage,
  isLoading,
  children,
  showConversation,
}: MainLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="h-screen flex bg-white">
      {/* Sidebar */}
      <Sidebar
        isCollapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        savedDashboards={savedDashboards}
        onLoadDashboard={onLoadDashboard}
        onNewDashboard={onNewDashboard}
        currentDashboardId={currentDashboardId}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {showConversation ? (
          <>
            {/* Conversation Pane */}
            <div className="w-1/2 border-r border-gray-200">
              <ConversationPane
                messages={messages}
                onSendMessage={onSendMessage}
                isLoading={isLoading}
              />
            </div>

            {/* Dashboard Content */}
            <div className="w-1/2 overflow-auto">{children}</div>
          </>
        ) : (
          /* Full Width Content (for intro page) */
          <div className="flex-1 overflow-auto">{children}</div>
        )}
      </div>
    </div>
  );
});

export default MainLayout;

export type { Message };
