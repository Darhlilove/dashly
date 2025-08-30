import { Dashboard } from "../types";

interface IntroPageProps {
  onFileUpload: (file: File) => void;
  onDemoData: () => void;
  isLoading: boolean;
  error: string | null;
  savedDashboards: Dashboard[];
  onLoadDashboard: (dashboard: Dashboard) => void;
}

export default function IntroPage({
  onFileUpload,
  onDemoData,
  isLoading,
  error,
  savedDashboards,
  onLoadDashboard,
}: IntroPageProps) {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileUpload(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      onFileUpload(file);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-full p-8">
      <div className="max-w-2xl w-full text-center">
        {/* Logo/Title */}
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-black mb-4 font-brand">
            dashly
          </h1>
          <p className="text-lg text-gray-600">
            Transform your data into insights with natural language
          </p>
        </div>

        {/* Upload Area */}
        <div className="mb-8">
          <div
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            className="border-2 border-dashed border-gray-300 p-12 hover:border-gray-400 transition-colors duration-200"
          >
            <div className="flex flex-col items-center">
              <svg
                className="w-12 h-12 text-gray-400 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>

              <h3 className="text-lg font-medium text-black mb-2">
                Upload your data
              </h3>
              <p className="text-gray-500 mb-6">
                Drag and drop a CSV file here, or click to browse
              </p>

              <div className="flex gap-4">
                <label className="btn-primary cursor-pointer">
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    disabled={isLoading}
                    className="sr-only"
                  />
                  Choose File
                </label>

                <button
                  onClick={onDemoData}
                  disabled={isLoading}
                  className="btn-secondary"
                >
                  Use Demo Data
                </button>
              </div>
            </div>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-white border border-red-600 border-l-4 text-black">
              {error}
            </div>
          )}
        </div>

        {/* Recent Dashboards */}
        {savedDashboards.length > 0 && (
          <div className="text-left">
            <h2 className="text-xl font-semibold text-black mb-4">
              Recent Dashboards
            </h2>
            <div className="grid gap-3">
              {savedDashboards.slice(0, 3).map((dashboard) => (
                <button
                  key={dashboard.id}
                  onClick={() => onLoadDashboard(dashboard)}
                  className="p-4 text-left border border-gray-200 hover:border-gray-300 transition-colors duration-200"
                >
                  <div className="flex items-center gap-3">
                    <svg
                      className="w-5 h-5 text-gray-400 flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                      />
                    </svg>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-black truncate">
                        {dashboard.name}
                      </div>
                      <div className="text-sm text-gray-500 truncate">
                        {dashboard.question}
                      </div>
                    </div>
                    <svg
                      className="w-4 h-4 text-gray-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Features */}
        <div className="mt-12 grid md:grid-cols-3 gap-8 text-center">
          <div>
            <div className="w-12 h-12 bg-red-100 mx-auto mb-4 flex items-center justify-center">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-4l-4 4z"
                />
              </svg>
            </div>
            <h3 className="font-semibold text-black mb-2">Natural Language</h3>
            <p className="text-gray-600 text-sm">
              Ask questions in plain English and get instant visualizations
            </p>
          </div>

          <div>
            <div className="w-12 h-12 bg-red-100 mx-auto mb-4 flex items-center justify-center">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
            </div>
            <h3 className="font-semibold text-black mb-2">Auto Charts</h3>
            <p className="text-gray-600 text-sm">
              Automatically generates the best chart type for your data
            </p>
          </div>

          <div>
            <div className="w-12 h-12 bg-red-100 mx-auto mb-4 flex items-center justify-center">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
                />
              </svg>
            </div>
            <h3 className="font-semibold text-black mb-2">Save & Share</h3>
            <p className="text-gray-600 text-sm">
              Save your dashboards and access them anytime
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
