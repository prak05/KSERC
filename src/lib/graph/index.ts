import { StateGraph, START, END } from "@langchain/langgraph";
import { TruingUpState } from "./state";
import { extractorNode, auditorNode, drafterNode } from "./agents";

// Build the LangGraph
const workflow = new StateGraph(TruingUpState)
    .addNode("extract", extractorNode)
    .addNode("audit", auditorNode)
    .addNode("draft", drafterNode)
    .addEdge(START, "extract")
    .addEdge("extract", "audit")
    .addEdge("audit", "draft")
    .addEdge("draft", END);

// Compile the graph
export const truingUpGraph = workflow.compile();

export async function runTruingUpPipeline(caseData: any) {
    const initialState = {
        caseData,
        costHeadsSummary: "",
        approvedExpenses: {},
        disallowances: [],
        totalClaimed: 0,
        totalApproved: 0,
        revenueGapSurplus: 0,
        draftNarrative: ""
    };

    const result = await truingUpGraph.invoke(initialState, {
        configurable: { thread_id: "default" }
    });

    return result;
}
