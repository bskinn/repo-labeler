import argparse as ap
import json
import os
from pathlib import Path

import requests as rq


def get_args():
    prs = ap.ArgumentParser(
        description="Utility to auto-apply a standard set of GitHub issue labels"
    )

    prs.add_argument(
        "repo",
        help="owner/repo to apply labels to, as '<owner>/<repo>'",
    )
    prs.add_argument(
        "--delete-default",
        help="Also delete the GitHub-default labels, if they exist",
        action="store_true",
        dest="delete_default",
    )

    return vars(prs.parse_args())


def main():
    args = get_args()

    repo = args["repo"]

    PAT = os.environ.get("GITHUB_PAT")

    HEADERS = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {PAT}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    API_URL_BASE = f"https://api.github.com/repos/{repo}/labels"

    labelsets = json.loads(Path("labels.json").read_text(encoding="utf-8"))

    for labelset in labelsets:
        set_name = labelset["name"]
        color = labelset["color"]
        labels = labelset["labels"]

        for label in labels:
            label_name = f"{set_name}: {label['name']} :{label['icon']}:"

            get_resp = rq.get(
                API_URL_BASE + f"/{label_name}",
                headers=HEADERS,
            )

            if get_resp.ok:
                # Label found, so let's update in place, but only if
                # we need to. We know the name isn't changing, so
                # we only need to check the color and description
                if (gr_json := get_resp.json())["description"] == label.get(
                    "text", ""
                ) and gr_json["color"] == color:
                    resp = get_resp
                    action = "unchanged"
                else:
                    resp = rq.patch(
                        API_URL_BASE + f"/{label_name}",
                        headers=HEADERS,
                        data=json.dumps(
                            {
                                "new_name": label_name,
                                "description": f"{label.get('text', '')}",
                                "color": color,
                            }
                        ),
                    )
                    action = "updated"
            else:
                # Not found, let's create
                resp = rq.post(
                    API_URL_BASE,
                    headers=HEADERS,
                    data=json.dumps(
                        {
                            "name": label_name,
                            "description": f"{label.get('text', '')}",
                            "color": color,
                        },
                    ),
                )
                action = "created"

            print(
                f"Label '{label_name}' result: {resp.status_code} ({resp.reason}) ({action})"  # noqa: E501
            )


if __name__ == "__main__":
    main()
