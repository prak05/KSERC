import { Annotation } from "@langchain/langgraph";

export const TruingUpState = Annotation.Root({
    caseData: Annotation<any>({
        reducer: (x, y) => y ?? x,
        default: () => ({}),
    }),
    costHeadsSummary: Annotation<string>({
        reducer: (x, y) => y ?? x,
        default: () => "",
    }),
    approvedExpenses: Annotation<Record<string, number>>({
        reducer: (x, y) => ({ ...x, ...y }),
        default: () => ({}),
    }),
    disallowances: Annotation<any[]>({
        reducer: (x, y) => x.concat(y),
        default: () => [],
    }),
    totalClaimed: Annotation<number>({
        reducer: (x, y) => y ?? x,
        default: () => 0,
    }),
    totalApproved: Annotation<number>({
        reducer: (x, y) => y ?? x,
        default: () => 0,
    }),
    revenueGapSurplus: Annotation<number>({
        reducer: (x, y) => y ?? x,
        default: () => 0,
    }),
    draftNarrative: Annotation<string>({
        reducer: (x, y) => y ?? x,
        default: () => "",
    }),
});
