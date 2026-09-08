import React, { useState, useEffect } from 'react';
import { Header } from './components/layout/Header';
import { ProjectGrid } from './components/hub/ProjectGrid';
import { NewProjectModal } from './components/hub/NewProjectModal';
import { SettingsModal } from './components/settings/SettingsModal';
import { ModernLoader } from './components/extraction/ModernLoader';
import { Workspace } from './components/layout/Workspace';
import { Project, ExtractionProgressEvent, CytoscapeGraphData } from './types';
import { api } from './services/api';

export const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [view, setView] = useState<'hub' | 'loading' | 'workspace'>('hub');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);

  // Extraction & Graph State
  const [progressEvent, setProgressEvent] = useState<ExtractionProgressEvent | null>(null);
  const [graphData, setGraphData] = useState<CytoscapeGraphData>({
    elements: { nodes: [], edges: [] },
    stats: { total_nodes: 0, total_edges: 0, types_count: {} },
  });
  const [minDegree, setMinDegree] = useState(1);
  const [selectedType, setSelectedType] = useState('all');

  // Load Projects on startup
  const loadProjects = async () => {
    try {
      const list = await api.getProjects();
      setProjects(list);
    } catch (err) {
      console.error('Failed to load projects', err);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  // Fetch graph data whenever currentProject, minDegree, or selectedType changes
  const loadGraph = async (projectId: string, deg = minDegree, type = selectedType) => {
    try {
      const data = await api.getGraph(projectId, deg, type);
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load graph data', err);
    }
  };

  const handleOpenProject = async (proj: Project) => {
    try {
      const detailed = await api.getProject(proj.id);
      setCurrentProject(detailed);
      if (detailed.status === 'completed') {
        await loadGraph(detailed.id);
        setView('workspace');
      } else if (detailed.status === 'processing') {
        setView('loading');
        listenToProgress(detailed.id, detailed.name);
      } else {
        setView('workspace');
      }
    } catch (err) {
      console.error('Error opening project', err);
    }
  };

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this project?')) return;
    try {
      await api.deleteProject(id);
      await loadProjects();
      if (currentProject?.id === id) {
        setCurrentProject(null);
        setView('hub');
      }
    } catch (err) {
      console.error('Error deleting project', err);
    }
  };

  const listenToProgress = (projectId: string, projName: string) => {
    let isTransitioning = false;
    let pollerInterval: any = null;

    const cleanup = () => {
      if (pollerInterval) {
        clearInterval(pollerInterval);
        pollerInterval = null;
      }
      try {
        eventSource.close();
      } catch (e) {}
    };

    const handleComplete = async () => {
      if (isTransitioning) return;
      isTransitioning = true;
      cleanup();

      try {
        const updated = await api.getProject(projectId);
        setCurrentProject(updated);
        await loadGraph(projectId);
        await loadProjects();
        setTimeout(() => {
          setView('workspace');
        }, 400);
      } catch (err) {
        console.error('Error transitioning to workspace:', err);
      }
    };

    const eventSource = new EventSource(`/api/v1/projects/${projectId}/progress`);

    eventSource.onmessage = async (event) => {
      try {
        const data: ExtractionProgressEvent = JSON.parse(event.data);
        setProgressEvent(data);

        if (data.stage === 'completed' || data.progress >= 1.0) {
          await handleComplete();
        } else if (data.stage === 'error') {
          cleanup();
          await loadProjects();
        }
      } catch (e) {}
    };

    eventSource.onerror = () => {
      // Fallback poller will maintain state and recover smoothly
    };

    // Resilient fallback poller every 1500ms
    pollerInterval = setInterval(async () => {
      try {
        const statusData = await api.getProjectStatus(projectId);
        if (statusData.latest_event) {
          setProgressEvent((prev) => ({
            ...prev,
            ...statusData.latest_event,
          }));
        }
        if (statusData.status === 'completed') {
          await handleComplete();
        } else if (statusData.status === 'failed') {
          cleanup();
          await loadProjects();
        }
      } catch (err) {}
    }, 1500);
  };

  const handleStartNewProject = async (payload: {
    name: string;
    description: string;
    files: File[];
    provider: string;
    endpoint: string;
    apiKey: string;
    model: string;
  }) => {
    try {
      // 1. Create Project
      const project = await api.createProject(payload.name, payload.description);

      // 2. Upload PDFs
      await api.uploadDocuments(project.id, payload.files);

      // 3. Start Extraction
      await api.startExtraction(project.id, {
        provider: payload.provider,
        endpoint: payload.endpoint,
        api_key: payload.apiKey,
        model: payload.model,
      });

      // 4. Update UI State & Listen to Progress
      setCurrentProject(project);
      setIsNewProjectOpen(false);
      setProgressEvent({
        project_id: project.id,
        stage: 'docling',
        progress: 0.05,
        message: 'Initializing extraction pipeline...',
        current_chunk: 0,
        total_chunks: 0,
        triples_found: 0,
        timestamp: Date.now() / 1000,
      });
      setView('loading');
      listenToProgress(project.id, project.name);
    } catch (err: any) {
      console.error('Failed to start extraction:', err);
      throw err;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#f8fafc] text-slate-800 overflow-hidden selection:bg-indigo-500 selection:text-white">
      {/* App Header */}
      <Header
        currentProject={view !== 'hub' ? currentProject : null}
        onNavigateHome={() => {
          setView('hub');
          loadProjects();
        }}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Main View Router */}
      <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
        {view === 'hub' && (
          <div className="flex-1 overflow-y-auto">
            <ProjectGrid
              projects={projects}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              onOpenProject={handleOpenProject}
              onDeleteProject={handleDeleteProject}
              onNewProject={() => setIsNewProjectOpen(true)}
            />
          </div>
        )}

        {view === 'loading' && (
          <div className="flex-1 overflow-y-auto">
            <ModernLoader
              progressEvent={progressEvent}
              projectName={currentProject?.name || 'Knowledge Extraction'}
              onBackToHub={() => {
                setView('hub');
                loadProjects();
              }}
            />
          </div>
        )}

        {view === 'workspace' && currentProject && (
          <Workspace
            project={currentProject}
            graphData={graphData}
            minDegree={minDegree}
            onMinDegreeChange={(deg) => setMinDegree(deg)}
            selectedType={selectedType}
            onSelectType={(type) => {
              setSelectedType(type);
            }}
          />
        )}
      </main>

      {/* Global Settings Modal */}
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      {/* New Project Initiator Modal */}
      <NewProjectModal
        isOpen={isNewProjectOpen}
        onClose={() => setIsNewProjectOpen(false)}
        onSubmit={handleStartNewProject}
      />
    </div>
  );
};

export default App;
