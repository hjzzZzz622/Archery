export interface DashboardDataResponse {
    dateRange: { startDate: string; endDate: string };
    charts: {
        workflowByDate: {
            dates: string[];
            counts: number[];
        };
    };
}