"""Plan templates for common scenarios."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanTemplate:
    """A reusable plan template."""

    id: str
    name: str
    description: str
    category: str
    steps: list[dict[str, Any]]
    estimated_duration: str | None = None
    tags: list[str] = field(default_factory=list)
    dependencies: dict[int, list[int]] = field(default_factory=dict)
    milestones: list[int] = field(default_factory=list)


class TemplateRegistry:
    """Registry of available plan templates."""

    def __init__(self):
        self._templates: dict[str, PlanTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self) -> None:
        """Register built-in templates."""
        templates = [
            self._create_trip_template(),
            self._create_event_template(),
            self._create_website_template(),
            self._create_mobile_app_template(),
            self._create_product_launch_template(),
            self._create_wedding_template(),
            self._create_job_hunt_template(),
            self._create_content_creation_template(),
            self._create_home_renovation_template(),
            self._create_study_plan_template(),
            self._create_business_plan_template(),
            self._create_fitness_goal_template(),
        ]

        for template in templates:
            self._templates[template.id] = template

    def _create_trip_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="trip",
            name="Trip Planning",
            description="Plan a complete trip with destinations, bookings, and activities",
            category="travel",
            estimated_duration="2-8 weeks",
            tags=["travel", "vacation", "planning"],
            steps=[
                {
                    "id": 1,
                    "description": "Choose destination and travel dates",
                    "status": "pending",
                },
                {
                    "id": 2,
                    "description": "Research visa and entry requirements",
                    "status": "pending",
                },
                {"id": 3, "description": "Book flights or transportation", "status": "pending"},
                {"id": 4, "description": "Book accommodation", "status": "pending"},
                {
                    "id": 5,
                    "description": "Create itinerary with key attractions",
                    "status": "pending",
                },
                {"id": 6, "description": "Arrange travel insurance", "status": "pending"},
                {"id": 7, "description": "Prepare packing list and documents", "status": "pending"},
                {"id": 8, "description": "Set up local currency and payments", "status": "pending"},
                {
                    "id": 9,
                    "description": "Book restaurant reservations if needed",
                    "status": "pending",
                },
                {
                    "id": 10,
                    "description": "Final check-in and departure preparation",
                    "status": "pending",
                },
            ],
            milestones=[3, 4, 7],
        )

    def _create_event_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="event",
            name="Event Planning",
            description="Organize an event from concept to execution",
            category="events",
            estimated_duration="4-12 weeks",
            tags=["event", "party", "organization"],
            steps=[
                {"id": 1, "description": "Define event purpose and goals", "status": "pending"},
                {"id": 2, "description": "Set budget and allocate resources", "status": "pending"},
                {"id": 3, "description": "Choose date and venue", "status": "pending"},
                {
                    "id": 4,
                    "description": "Create guest list and send invitations",
                    "status": "pending",
                },
                {"id": 5, "description": "Arrange catering and menu", "status": "pending"},
                {"id": 6, "description": "Plan entertainment and activities", "status": "pending"},
                {"id": 7, "description": "Coordinate decorations and theme", "status": "pending"},
                {"id": 8, "description": "Arrange transportation if needed", "status": "pending"},
                {
                    "id": 9,
                    "description": "Prepare event schedule and timeline",
                    "status": "pending",
                },
                {
                    "id": 10,
                    "description": "Execute event and handle day-of logistics",
                    "status": "pending",
                },
                {"id": 11, "description": "Follow-up and gather feedback", "status": "pending"},
            ],
            milestones=[3, 4, 10],
        )

    def _create_website_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="website",
            name="Website Development",
            description="Build a complete website from design to deployment",
            category="development",
            estimated_duration="4-8 weeks",
            tags=["web", "development", "coding"],
            steps=[
                {
                    "id": 1,
                    "description": "Define website goals and target audience",
                    "status": "pending",
                },
                {
                    "id": 2,
                    "description": "Create sitemap and content structure",
                    "status": "pending",
                },
                {"id": 3, "description": "Design wireframes and mockups", "status": "pending"},
                {
                    "id": 4,
                    "description": "Choose technology stack and hosting",
                    "status": "pending",
                },
                {"id": 5, "description": "Develop frontend UI components", "status": "pending"},
                {"id": 6, "description": "Develop backend and database", "status": "pending"},
                {"id": 7, "description": "Create and populate content", "status": "pending"},
                {"id": 8, "description": "Implement SEO and analytics", "status": "pending"},
                {
                    "id": 9,
                    "description": "Test functionality and responsiveness",
                    "status": "pending",
                },
                {"id": 10, "description": "Deploy to production", "status": "pending"},
                {"id": 11, "description": "Post-launch monitoring and fixes", "status": "pending"},
            ],
            milestones=[3, 6, 10],
            dependencies={5: [4], 6: [4], 9: [5, 6, 7]},
        )

    def _create_mobile_app_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="mobile_app",
            name="Mobile App Development",
            description="Build a mobile application for iOS and Android",
            category="development",
            estimated_duration="8-16 weeks",
            tags=["mobile", "app", "development"],
            steps=[
                {
                    "id": 1,
                    "description": "Define app concept and unique value proposition",
                    "status": "pending",
                },
                {
                    "id": 2,
                    "description": "Research competitors and market fit",
                    "status": "pending",
                },
                {
                    "id": 3,
                    "description": "Create user personas and user stories",
                    "status": "pending",
                },
                {
                    "id": 4,
                    "description": "Design app architecture and tech stack",
                    "status": "pending",
                },
                {
                    "id": 5,
                    "description": "Create wireframes and UI/UX designs",
                    "status": "pending",
                },
                {
                    "id": 6,
                    "description": "Set up development environment and CI/CD",
                    "status": "pending",
                },
                {"id": 7, "description": "Develop core features (MVP)", "status": "pending"},
                {
                    "id": 8,
                    "description": "Implement authentication and security",
                    "status": "pending",
                },
                {"id": 9, "description": "Build backend API and database", "status": "pending"},
                {"id": 10, "description": "Integrate third-party services", "status": "pending"},
                {"id": 11, "description": "Conduct internal testing and QA", "status": "pending"},
                {"id": 12, "description": "Beta testing with users", "status": "pending"},
                {"id": 13, "description": "Prepare app store listings", "status": "pending"},
                {
                    "id": 14,
                    "description": "Submit to App Store and Play Store",
                    "status": "pending",
                },
                {"id": 15, "description": "Launch and monitor metrics", "status": "pending"},
            ],
            milestones=[5, 7, 12, 14],
            dependencies={7: [4, 5], 8: [7], 9: [4], 10: [7, 9], 11: [7, 8, 10]},
        )

    def _create_product_launch_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="product_launch",
            name="Product Launch",
            description="Launch a new product with marketing and sales strategy",
            category="business",
            estimated_duration="6-12 weeks",
            tags=["product", "launch", "marketing"],
            steps=[
                {
                    "id": 1,
                    "description": "Finalize product specifications and pricing",
                    "status": "pending",
                },
                {
                    "id": 2,
                    "description": "Define target market and positioning",
                    "status": "pending",
                },
                {
                    "id": 3,
                    "description": "Create marketing strategy and messaging",
                    "status": "pending",
                },
                {
                    "id": 4,
                    "description": "Develop sales materials and presentations",
                    "status": "pending",
                },
                {"id": 5, "description": "Set up distribution channels", "status": "pending"},
                {
                    "id": 6,
                    "description": "Create launch website and landing pages",
                    "status": "pending",
                },
                {"id": 7, "description": "Plan launch event or announcement", "status": "pending"},
                {
                    "id": 8,
                    "description": "Prepare press releases and media kit",
                    "status": "pending",
                },
                {
                    "id": 9,
                    "description": "Coordinate with influencers and partners",
                    "status": "pending",
                },
                {"id": 10, "description": "Set up customer support processes", "status": "pending"},
                {"id": 11, "description": "Execute launch campaign", "status": "pending"},
                {
                    "id": 12,
                    "description": "Monitor results and gather feedback",
                    "status": "pending",
                },
            ],
            milestones=[3, 6, 11],
        )

    def _create_wedding_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="wedding",
            name="Wedding Planning",
            description="Plan a wedding ceremony and reception",
            category="events",
            estimated_duration="6-18 months",
            tags=["wedding", "marriage", "celebration"],
            steps=[
                {"id": 1, "description": "Set overall budget and priorities", "status": "pending"},
                {"id": 2, "description": "Create preliminary guest list", "status": "pending"},
                {"id": 3, "description": "Choose wedding date and season", "status": "pending"},
                {"id": 4, "description": "Book ceremony and reception venues", "status": "pending"},
                {
                    "id": 5,
                    "description": "Hire wedding planner or coordinator",
                    "status": "pending",
                },
                {"id": 6, "description": "Book photographer and videographer", "status": "pending"},
                {"id": 7, "description": "Book caterer and finalize menu", "status": "pending"},
                {"id": 8, "description": "Order wedding dress and attire", "status": "pending"},
                {
                    "id": 9,
                    "description": "Book florist and choose decorations",
                    "status": "pending",
                },
                {"id": 10, "description": "Arrange transportation", "status": "pending"},
                {"id": 11, "description": "Book officiant or ceremony leader", "status": "pending"},
                {"id": 12, "description": "Send save-the-dates", "status": "pending"},
                {"id": 13, "description": "Book entertainment (DJ/band)", "status": "pending"},
                {"id": 14, "description": "Plan honeymoon", "status": "pending"},
                {"id": 15, "description": "Send formal invitations", "status": "pending"},
                {
                    "id": 16,
                    "description": "Finalize ceremony details and vows",
                    "status": "pending",
                },
                {
                    "id": 17,
                    "description": "Rehearsal dinner and final walkthrough",
                    "status": "pending",
                },
                {"id": 18, "description": "Wedding day execution", "status": "pending"},
            ],
            milestones=[4, 8, 12, 15, 18],
        )

    def _create_job_hunt_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="job_hunt",
            name="Job Search",
            description="Organized approach to finding a new job",
            category="career",
            estimated_duration="4-16 weeks",
            tags=["career", "job", "employment"],
            steps=[
                {"id": 1, "description": "Update resume and LinkedIn profile", "status": "pending"},
                {"id": 2, "description": "Define target roles and companies", "status": "pending"},
                {
                    "id": 3,
                    "description": "Research salary ranges and market rates",
                    "status": "pending",
                },
                {"id": 4, "description": "Create cover letter templates", "status": "pending"},
                {
                    "id": 5,
                    "description": "Set up job alerts on major platforms",
                    "status": "pending",
                },
                {"id": 6, "description": "Apply to 5-10 positions per week", "status": "pending"},
                {
                    "id": 7,
                    "description": "Network and request informational interviews",
                    "status": "pending",
                },
                {
                    "id": 8,
                    "description": "Prepare for common interview questions",
                    "status": "pending",
                },
                {"id": 9, "description": "Practice technical assessments", "status": "pending"},
                {"id": 10, "description": "Follow up on applications", "status": "pending"},
                {"id": 11, "description": "Attend interviews and debrief", "status": "pending"},
                {
                    "id": 12,
                    "description": "Evaluate offers and negotiate terms",
                    "status": "pending",
                },
                {
                    "id": 13,
                    "description": "Accept offer and prepare for transition",
                    "status": "pending",
                },
            ],
            milestones=[2, 6, 12],
        )

    def _create_content_creation_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="content_creation",
            name="Content Creation Series",
            description="Plan and execute a content series (blog, video, podcast)",
            category="creative",
            estimated_duration="4-8 weeks",
            tags=["content", "creative", "media"],
            steps=[
                {"id": 1, "description": "Define content niche and audience", "status": "pending"},
                {
                    "id": 2,
                    "description": "Research trending topics and keywords",
                    "status": "pending",
                },
                {
                    "id": 3,
                    "description": "Create content calendar with topics",
                    "status": "pending",
                },
                {
                    "id": 4,
                    "description": "Set up necessary equipment and tools",
                    "status": "pending",
                },
                {"id": 5, "description": "Produce first batch of content", "status": "pending"},
                {"id": 6, "description": "Edit and polish content", "status": "pending"},
                {
                    "id": 7,
                    "description": "Create thumbnails and promotional assets",
                    "status": "pending",
                },
                {"id": 8, "description": "Schedule and publish content", "status": "pending"},
                {"id": 9, "description": "Promote on social media channels", "status": "pending"},
                {
                    "id": 10,
                    "description": "Engage with audience and respond to comments",
                    "status": "pending",
                },
                {"id": 11, "description": "Analyze performance metrics", "status": "pending"},
                {
                    "id": 12,
                    "description": "Iterate based on feedback and data",
                    "status": "pending",
                },
            ],
            milestones=[3, 6, 8],
        )

    def _create_home_renovation_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="home_renovation",
            name="Home Renovation Project",
            description="Plan a home renovation from design to completion",
            category="home",
            estimated_duration="8-24 weeks",
            tags=["home", "renovation", "construction"],
            steps=[
                {"id": 1, "description": "Define renovation scope and goals", "status": "pending"},
                {"id": 2, "description": "Set budget including contingency", "status": "pending"},
                {
                    "id": 3,
                    "description": "Research and hire architect/designer",
                    "status": "pending",
                },
                {
                    "id": 4,
                    "description": "Create design plans and 3D renderings",
                    "status": "pending",
                },
                {"id": 5, "description": "Obtain necessary permits", "status": "pending"},
                {"id": 6, "description": "Get quotes from contractors", "status": "pending"},
                {"id": 7, "description": "Select and hire contractor", "status": "pending"},
                {"id": 8, "description": "Order materials and fixtures", "status": "pending"},
                {
                    "id": 9,
                    "description": "Prepare space and protect furniture",
                    "status": "pending",
                },
                {"id": 10, "description": "Execute demolition phase", "status": "pending"},
                {"id": 11, "description": "Complete structural work", "status": "pending"},
                {"id": 12, "description": "Install electrical and plumbing", "status": "pending"},
                {
                    "id": 13,
                    "description": "Complete finishing work and painting",
                    "status": "pending",
                },
                {"id": 14, "description": "Final inspection and cleanup", "status": "pending"},
                {"id": 15, "description": "Furnish and decorate", "status": "pending"},
            ],
            milestones=[4, 7, 11, 14],
            dependencies={
                5: [4],
                6: [4],
                7: [6],
                8: [7],
                9: [8],
                10: [9],
                11: [10],
                12: [11],
                13: [12],
            },
        )

    def _create_study_plan_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="study_plan",
            name="Exam Study Plan",
            description="Structured preparation plan for exams or certifications",
            category="education",
            estimated_duration="4-12 weeks",
            tags=["education", "study", "exam"],
            steps=[
                {
                    "id": 1,
                    "description": "Review exam syllabus and requirements",
                    "status": "pending",
                },
                {"id": 2, "description": "Assess current knowledge level", "status": "pending"},
                {
                    "id": 3,
                    "description": "Gather study materials and resources",
                    "status": "pending",
                },
                {"id": 4, "description": "Create detailed study schedule", "status": "pending"},
                {"id": 5, "description": "Study topic area 1", "status": "pending"},
                {"id": 6, "description": "Study topic area 2", "status": "pending"},
                {"id": 7, "description": "Study topic area 3", "status": "pending"},
                {"id": 8, "description": "Complete practice questions set 1", "status": "pending"},
                {"id": 9, "description": "Review weak areas identified", "status": "pending"},
                {"id": 10, "description": "Complete full practice exam 1", "status": "pending"},
                {"id": 11, "description": "Study topic area 4", "status": "pending"},
                {"id": 12, "description": "Complete practice questions set 2", "status": "pending"},
                {"id": 13, "description": "Complete full practice exam 2", "status": "pending"},
                {"id": 14, "description": "Final review of all topics", "status": "pending"},
                {
                    "id": 15,
                    "description": "Exam day preparation and execution",
                    "status": "pending",
                },
            ],
            milestones=[4, 10, 13, 15],
            dependencies={8: [5, 6, 7], 9: [8], 10: [8, 9], 12: [11], 13: [12]},
        )

    def _create_business_plan_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="business_plan",
            name="Business Plan Development",
            description="Create a comprehensive business plan for a new venture",
            category="business",
            estimated_duration="4-8 weeks",
            tags=["business", "startup", "entrepreneurship"],
            steps=[
                {"id": 1, "description": "Define business concept and vision", "status": "pending"},
                {
                    "id": 2,
                    "description": "Conduct market research and analysis",
                    "status": "pending",
                },
                {
                    "id": 3,
                    "description": "Analyze competitors and positioning",
                    "status": "pending",
                },
                {"id": 4, "description": "Define target customer personas", "status": "pending"},
                {"id": 5, "description": "Develop value proposition", "status": "pending"},
                {"id": 6, "description": "Create revenue model and pricing", "status": "pending"},
                {"id": 7, "description": "Build financial projections", "status": "pending"},
                {"id": 8, "description": "Plan marketing and sales strategy", "status": "pending"},
                {"id": 9, "description": "Define operational plan", "status": "pending"},
                {
                    "id": 10,
                    "description": "Identify key team and resources needed",
                    "status": "pending",
                },
                {
                    "id": 11,
                    "description": "Assess risks and mitigation strategies",
                    "status": "pending",
                },
                {"id": 12, "description": "Write executive summary", "status": "pending"},
                {"id": 13, "description": "Compile and review full plan", "status": "pending"},
                {"id": 14, "description": "Prepare pitch deck", "status": "pending"},
                {
                    "id": 15,
                    "description": "Present to stakeholders or investors",
                    "status": "pending",
                },
            ],
            milestones=[4, 7, 13, 15],
        )

    def _create_fitness_goal_template(self) -> PlanTemplate:
        return PlanTemplate(
            id="fitness_goal",
            name="Fitness Goal Achievement",
            description="Structured plan to reach a specific fitness goal",
            category="health",
            estimated_duration="8-16 weeks",
            tags=["fitness", "health", "workout"],
            steps=[
                {"id": 1, "description": "Define specific fitness goal", "status": "pending"},
                {"id": 2, "description": "Assess current fitness level", "status": "pending"},
                {
                    "id": 3,
                    "description": "Consult with fitness professional if needed",
                    "status": "pending",
                },
                {"id": 4, "description": "Create workout schedule", "status": "pending"},
                {"id": 5, "description": "Plan nutrition and meal prep", "status": "pending"},
                {"id": 6, "description": "Weeks 1-2: Foundation phase", "status": "pending"},
                {"id": 7, "description": "Weeks 3-4: Building consistency", "status": "pending"},
                {"id": 8, "description": "Weeks 5-6: Progressive overload", "status": "pending"},
                {"id": 9, "description": "Weeks 7-8: Mid-point assessment", "status": "pending"},
                {"id": 10, "description": "Weeks 9-10: Intensification", "status": "pending"},
                {"id": 11, "description": "Weeks 11-12: Peak training", "status": "pending"},
                {"id": 12, "description": "Weeks 13-14: Refinement", "status": "pending"},
                {
                    "id": 13,
                    "description": "Weeks 15-16: Final preparation and goal attempt",
                    "status": "pending",
                },
                {
                    "id": 14,
                    "description": "Evaluate results and set next goal",
                    "status": "pending",
                },
            ],
            milestones=[4, 9, 13, 14],
        )

    def get_template(self, template_id: str) -> PlanTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self, category: str | None = None) -> list[PlanTemplate]:
        """List all templates, optionally filtered by category."""
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        return sorted(templates, key=lambda t: t.name)

    def get_categories(self) -> list[str]:
        """Get all unique template categories."""
        return sorted(set(t.category for t in self._templates.values()))

    def search_templates(self, query: str) -> list[PlanTemplate]:
        """Search templates by name or description."""
        query_lower = query.lower()
        matches = []

        for template in self._templates.values():
            if (
                query_lower in template.name.lower()
                or query_lower in template.description.lower()
                or any(query_lower in tag.lower() for tag in template.tags)
            ):
                matches.append(template)

        return matches


class TemplateApplicator:
    """Applies templates to create new plans."""

    def __init__(self, registry: TemplateRegistry | None = None):
        self._registry = registry or TemplateRegistry()

    def apply_template(
        self,
        template_id: str,
        custom_title: str | None = None,
    ) -> dict[str, Any] | None:
        """Apply a template to create a new plan dictionary."""
        template = self._registry.get_template(template_id)
        if not template:
            return None

        from datetime import datetime

        timestamp = datetime.now().isoformat()

        return {
            "title": custom_title or template.name,
            "steps": [dict(step) for step in template.steps],
            "version": 1,
            "created_at": timestamp,
            "updated_at": timestamp,
            "history": [
                {
                    "version": 1,
                    "timestamp": timestamp,
                    "action": "created",
                    "title": custom_title or template.name,
                    "steps": [dict(step) for step in template.steps],
                }
            ],
            "summary": f"Plan for {custom_title or template.name} with {len(template.steps)} steps.",
            "metadata": {
                "total_steps": len(template.steps),
                "completed_steps": 0,
                "status": "draft",
                "template_id": template_id,
                "estimated_duration": template.estimated_duration,
                "dependencies": template.dependencies,
                "milestones": template.milestones,
            },
            "tags": [],
        }

    def get_template_preview(self, template_id: str) -> dict[str, Any] | None:
        """Get a preview of a template without creating a plan."""
        template = self._registry.get_template(template_id)
        if not template:
            return None

        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "estimated_duration": template.estimated_duration,
            "step_count": len(template.steps),
            "tags": template.tags,
            "has_dependencies": bool(template.dependencies),
            "has_milestones": bool(template.milestones),
        }
